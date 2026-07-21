from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import dataclass
from http import HTTPStatus
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from runtime.epistemic_orchestra.canonical import exact_text_sha256
from runtime.epistemic_orchestra.live_session import consume_live_stage_authorization
from runtime.providers.orchestra_live_service import (
    OrchestraLiveWebError,
    OrchestraLiveWebService,
)
from runtime.providers.user_connections import UserProviderStore
from runtime.webapp import CodexStyleHandler, route_get_payload, route_post_payload


@dataclass(frozen=True)
class _TestConnectionResult:
    success: bool
    connection_id: str
    model_profile_id: str
    remote_model_id: str
    tested_at_epoch: int

    def to_dict(self) -> dict[str, object]:
        return {
            "success": self.success,
            "connection_id": self.connection_id,
            "model_profile_id": self.model_profile_id,
            "remote_model_id": self.remote_model_id,
            "latency_ms": 1,
            "response_preview": "AOIA_CONNECTION_OK",
            "tested_at_epoch": self.tested_at_epoch,
            "trust_status": "UNTRUSTED",
            "authority_status": "NON_AUTHORITATIVE",
            "authoritative": False,
            "can_approve": False,
            "can_write": False,
            "can_execute": False,
            "can_satisfy_gate": False,
        }


class _FakeExactInvoker:
    def __init__(self, store: UserProviderStore) -> None:
        self.store = store
        self.calls: list[tuple[str, str]] = []
        self.fail_role: str | None = None

    def authorize_connection_test(self, **kwargs):
        if kwargs["explicit_operator_action"] is not True:
            raise ValueError("explicit action required")
        connection = self.store.get_connection(kwargs["connection_id"])
        profile = self.store.get_model_profile(kwargs["model_profile_id"])
        if self.store.credential_status(connection.credential_reference) != "configured":
            raise ValueError("credential missing")
        return SimpleNamespace(connection=connection, profile=profile)

    def test_connection(self, authorization, *, current_epoch: int):
        return _TestConnectionResult(
            success=True,
            connection_id=authorization.connection.connection_id,
            model_profile_id=authorization.profile.model_profile_id,
            remote_model_id=authorization.profile.remote_model_id,
            tested_at_epoch=current_epoch,
        )

    def invoke_exact(
        self,
        *,
        stage_authorization,
        binding,
        prompt: str,
        max_tokens: int,
        timeout_seconds: int,
    ):
        consume_live_stage_authorization(
            stage_authorization,
            binding=binding,
            provider_prompt=prompt,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
        )
        self.calls.append((binding.model_profile_id, binding.operator_role))
        if binding.operator_role == self.fail_role:
            raise TimeoutError("secret-bearing provider detail must stay hidden")
        if binding.operator_role in {"CRITIC", "AUDITOR"}:
            response = json.dumps(
                {"critic_outcome": "NO_MATERIAL_ISSUE_FOUND", "issues": []},
                sort_keys=True,
                separators=(",", ":"),
            )
        elif binding.operator_role == "SYNTHESIZER":
            response = "Non-authoritative synthesized draft."
        else:
            response = "Non-authoritative main draft."
        return SimpleNamespace(
            binding_hash=binding.binding_hash,
            connection_id=binding.connection_id,
            model_profile_id=binding.model_profile_id,
            remote_model_id=binding.remote_model_id,
            response_text=response,
            trust_status="UNTRUSTED",
            authority_status="NON_AUTHORITATIVE",
            authoritative=False,
            can_approve=False,
            can_write=False,
            can_execute=False,
            can_satisfy_gate=False,
        )


class OrchestraUserProviderWebApi1ATests(unittest.TestCase):
    API_KEY = "sk-live-web-api-test-secret-material-000001"

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = UserProviderStore(
            root / "project",
            state_root=root / "state",
            secrets_root=root / "secrets",
        )
        self.fake_invoker = _FakeExactInvoker(self.store)
        self.service = OrchestraLiveWebService(
            root / "project",
            store=self.store,
            exact_invoker=self.fake_invoker,  # type: ignore[arg-type]
            clock=lambda: 1_800_000_000,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _add_connection(self) -> dict[str, object]:
        return self.service.create_connection(
            {
                "connection_id": "user-openrouter",
                "display_name": "User OpenRouter",
                "api_style": "openai_compatible",
                "base_url": "https://openrouter.ai/api/v1",
                "api_key": self.API_KEY,
            }
        )

    def _add_models(self, count: int = 3) -> None:
        self._add_connection()
        roles = ("MAIN", "CRITIC", "AUDITOR", "SYNTHESIZER")
        for index in range(count):
            self.service.create_model_profile(
                {
                    "model_profile_id": f"model-{index}",
                    "connection_id": "user-openrouter",
                    "display_name": f"Model {index}",
                    "remote_model_id": f"example/model-{index}",
                    "allowed_roles": list(roles),
                }
            )

    @staticmethod
    def _selection(count: int) -> list[dict[str, str]]:
        roles = ["MAIN", "CRITIC", "AUDITOR", "SYNTHESIZER"]
        return [
            {"model_profile_id": f"model-{index}", "role": roles[index]}
            for index in range(count)
        ]

    def test_connection_and_model_routes_never_return_or_commit_api_key(self) -> None:
        created = self._add_connection()
        serialized = json.dumps(created, sort_keys=True)
        self.assertNotIn(self.API_KEY, serialized)
        self.assertNotIn("api_key", created)
        self.assertNotIn(self.API_KEY, self.store.config_path.read_text(encoding="utf-8"))
        self.assertEqual("configured", created["connection"]["credential_status"])

    def test_configured_key_used_as_role_is_never_echoed_by_service_errors(self) -> None:
        self._add_connection()
        with self.assertRaises(OrchestraLiveWebError) as caught:
            self.service.create_model_profile(
                {
                    "model_profile_id": "unsafe-role-model",
                    "connection_id": "user-openrouter",
                    "display_name": "Unsafe Role Model",
                    "remote_model_id": "example/unsafe-role-model",
                    "allowed_roles": [self.API_KEY],
                }
            )
        self.assertNotIn(self.API_KEY, str(caught.exception))

        model = self.service.create_model_profile(
            {
                "model_profile_id": "model-main",
                "connection_id": "user-openrouter",
                "display_name": "Main model",
                "remote_model_id": "example/main",
                "allowed_roles": ["MAIN"],
            }
        )
        self.assertNotIn(self.API_KEY, json.dumps(model, sort_keys=True))

    def test_model_table_is_dynamic_and_reports_only_masked_credential_status(self) -> None:
        self._add_models(3)
        payload = self.service.list_orchestra_models()
        self.assertEqual(3, len(payload["models"]))
        self.assertTrue(all(row["credential_status"] == "configured" for row in payload["models"]))
        self.assertNotIn(self.API_KEY, json.dumps(payload, sort_keys=True))
        self.assertEqual(["MAIN", "CRITIC", "AUDITOR", "SYNTHESIZER"], payload["supported_roles"])

    def test_connection_test_requires_actual_boolean_and_records_bounded_status(self) -> None:
        self._add_models(2)
        with self.assertRaisesRegex(OrchestraLiveWebError, "must be boolean"):
            self.service.test_connection(
                {
                    "connection_id": "user-openrouter",
                    "model_profile_id": "model-0",
                    "explicit_operator_action": "true",
                }
            )
        result = self.service.test_connection(
            {
                "connection_id": "user-openrouter",
                "model_profile_id": "model-0",
                "explicit_operator_action": True,
            }
        )
        self.assertTrue(result["success"])
        self.assertFalse(result["authoritative"])
        row = self.service.list_orchestra_models()["models"][0]
        self.assertEqual("success", row["last_connection_test"]["status"])

    def test_preview_sorts_roles_and_server_retains_the_only_usable_plan(self) -> None:
        self._add_models(3)
        preview_payload = self.service.create_preview(
            {
                "source_prompt": "Review this bounded plan.",
                "selections": [
                    {"model_profile_id": "model-2", "role": "AUDITOR"},
                    {"model_profile_id": "model-1", "role": "CRITIC"},
                    {"model_profile_id": "model-0", "role": "MAIN"},
                ],
            }
        )
        roles = [item["operator_role"] for item in preview_payload["preview"]["planned_calls"]]
        self.assertEqual(["MAIN", "CRITIC", "AUDITOR"], roles)
        self.assertFalse(preview_payload["provider_call_permitted"])
        self.assertTrue(preview_payload["human_action_required"])

        preview_hash = preview_payload["preview"]["preview_hash"]
        with self.assertRaisesRegex(OrchestraLiveWebError, "fields"):
            self.service.run_preview(
                {
                    "preview_hash": preview_hash,
                    "confirmation_hash": preview_hash,
                    "confirmed_preview_hash": preview_hash,
                    "explicit_run_action": True,
                    "preview": preview_payload["preview"],
                }
            )
        self.assertEqual([], self.fake_invoker.calls)

    def test_three_exact_hashes_and_actual_run_action_are_required(self) -> None:
        self._add_models(2)
        preview = self.service.create_preview(
            {
                "source_prompt": "Prompt",
                "selections": self._selection(2),
            }
        )["preview"]
        preview_hash = preview["preview_hash"]
        with self.assertRaisesRegex(OrchestraLiveWebError, "must be boolean"):
            self.service.run_preview(
                {
                    "preview_hash": preview_hash,
                    "confirmation_hash": preview_hash,
                    "confirmed_preview_hash": preview_hash,
                    "explicit_run_action": "true",
                }
            )
        with self.assertRaisesRegex(OrchestraLiveWebError, "three confirmation hashes"):
            self.service.run_preview(
                {
                    "preview_hash": preview_hash,
                    "confirmation_hash": "0" * 64,
                    "confirmed_preview_hash": preview_hash,
                    "explicit_run_action": True,
                }
            )
        self.assertEqual([], self.fake_invoker.calls)
        with self.assertRaisesRegex(OrchestraLiveWebError, "missing, foreign, or consumed"):
            self.service.run_preview(
                {
                    "preview_hash": preview_hash,
                    "confirmation_hash": preview_hash,
                    "confirmed_preview_hash": preview_hash,
                    "explicit_run_action": True,
                }
            )
        self.assertEqual([], self.fake_invoker.calls)

    def test_run_is_single_use_and_outputs_remain_non_authoritative(self) -> None:
        self._add_models(3)
        preview = self.service.create_preview(
            {
                "source_prompt": "Produce and independently review a draft.",
                "selections": self._selection(3),
                "timeout_seconds": 10,
                "maximum_output_tokens": 128,
            }
        )["preview"]
        preview_hash = preview["preview_hash"]
        request = {
            "preview_hash": preview_hash,
            "confirmation_hash": preview_hash,
            "confirmed_preview_hash": preview_hash,
            "explicit_run_action": True,
        }
        result = self.service.run_preview(request)
        self.assertEqual(3, len(self.fake_invoker.calls))
        self.assertEqual(["MAIN", "CRITIC", "AUDITOR"], [role for _model, role in self.fake_invoker.calls])
        self.assertFalse(result["authoritative"])
        self.assertTrue(result["human_review_required"])
        self.assertFalse(result["automatic_fallback_used"])
        self.assertFalse(result["automatic_retry_used"])
        self.assertNotIn(self.API_KEY, json.dumps(result, sort_keys=True))
        with self.assertRaisesRegex(OrchestraLiveWebError, "missing, foreign, or consumed"):
            self.service.run_preview(request)
        self.assertEqual(3, len(self.fake_invoker.calls))

    def test_config_revision_change_invalidates_preview_before_provider_call(self) -> None:
        self._add_models(2)
        preview = self.service.create_preview(
            {"source_prompt": "Prompt", "selections": self._selection(2)}
        )["preview"]
        self.store.disable_model_profile("model-1")
        preview_hash = preview["preview_hash"]
        with self.assertRaisesRegex(OrchestraLiveWebError, "disabled"):
            self.service.run_preview(
                {
                    "preview_hash": preview_hash,
                    "confirmation_hash": preview_hash,
                    "confirmed_preview_hash": preview_hash,
                    "explicit_run_action": True,
                }
            )

    def test_configured_key_in_source_prompt_is_rejected_before_hashing(self) -> None:
        self._add_models(2)
        with self.assertRaises(OrchestraLiveWebError) as caught:
            self.service.create_preview(
                {
                    "source_prompt": f"Do not hash {self.API_KEY}",
                    "selections": self._selection(2),
                }
            )
        self.assertNotIn(self.API_KEY, str(caught.exception))
        self.assertEqual([], self.fake_invoker.calls)

    def test_unselected_connection_key_is_rejected_before_prompt_hashing(self) -> None:
        self._add_models(2)
        unselected_key = "sk-unselected-connection-secret-material-000002"
        self.service.create_connection(
            {
                "connection_id": "unselected-connection",
                "display_name": "Unselected Connection",
                "api_style": "openai_compatible",
                "base_url": "https://unselected.example.invalid/v1",
                "api_key": unselected_key,
            }
        )
        with self.assertRaises(OrchestraLiveWebError) as caught:
            self.service.create_preview(
                {
                    "source_prompt": f"Do not hash {unselected_key}",
                    "selections": self._selection(2),
                }
            )
        self.assertNotIn(unselected_key, str(caught.exception))
        self.assertEqual([], self.fake_invoker.calls)

    def test_configured_key_equal_to_source_hash_blocks_preview_publication(self) -> None:
        prompt = "Prompt chosen for a secret-hash collision regression."
        collision_key = exact_text_sha256(prompt)
        self.service.create_connection(
            {
                "connection_id": "hash-collision-connection",
                "display_name": "Hash Collision Connection",
                "api_style": "openai_compatible",
                "base_url": "https://collision.example.invalid/v1",
                "api_key": collision_key,
            }
        )
        for index, role in enumerate(("MAIN", "CRITIC")):
            self.service.create_model_profile(
                {
                    "model_profile_id": f"collision-model-{index}",
                    "connection_id": "hash-collision-connection",
                    "display_name": f"Collision Model {index}",
                    "remote_model_id": f"example/collision-{index}",
                    "allowed_roles": [role],
                }
            )
        with self.assertRaises(OrchestraLiveWebError) as caught:
            self.service.create_preview(
                {
                    "source_prompt": prompt,
                    "selections": [
                        {"model_profile_id": "collision-model-0", "role": "MAIN"},
                        {"model_profile_id": "collision-model-1", "role": "CRITIC"},
                    ],
                }
            )
        self.assertNotIn(collision_key, str(caught.exception))
        self.assertEqual({}, self.service._issued_previews)

    def test_credential_rotation_invalidates_stored_prompt_before_any_call(self) -> None:
        self._add_models(2)
        rotated_key = "sk-rotated-after-preview-secret-material-000003"
        preview = self.service.create_preview(
            {
                "source_prompt": f"Text that later equals {rotated_key}",
                "selections": self._selection(2),
            }
        )["preview"]
        self.store.save_credential("user-openrouter", rotated_key)
        preview_hash = preview["preview_hash"]
        with self.assertRaises(OrchestraLiveWebError) as caught:
            self.service.run_preview(
                {
                    "preview_hash": preview_hash,
                    "confirmation_hash": preview_hash,
                    "confirmed_preview_hash": preview_hash,
                    "explicit_run_action": True,
                }
            )
        self.assertNotIn(rotated_key, str(caught.exception))
        self.assertEqual([], self.fake_invoker.calls)
        with self.assertRaisesRegex(OrchestraLiveWebError, "missing, foreign, or consumed"):
            self.service.run_preview(
                {
                    "preview_hash": preview_hash,
                    "confirmation_hash": preview_hash,
                    "confirmed_preview_hash": preview_hash,
                    "explicit_run_action": True,
                }
            )

    def test_failed_stage_is_exposed_safely_and_session_is_consumed(self) -> None:
        self._add_models(2)
        self.fake_invoker.fail_role = "CRITIC"
        preview = self.service.create_preview(
            {"source_prompt": "Prompt", "selections": self._selection(2)}
        )["preview"]
        preview_hash = preview["preview_hash"]
        request = {
            "preview_hash": preview_hash,
            "confirmation_hash": preview_hash,
            "confirmed_preview_hash": preview_hash,
            "explicit_run_action": True,
        }
        result = self.service.run_preview(request)
        self.assertFalse(result["ok"])
        self.assertEqual("CRITIC", result["failed_stage"]["operator_role"])
        self.assertEqual("model-1", result["failed_stage"]["model_profile_id"])
        self.assertTrue(result["session_consumed"])
        self.assertFalse(result["automatic_retry_used"])
        self.assertFalse(result["automatic_fallback_used"])
        self.assertNotIn("provider detail", json.dumps(result, sort_keys=True))
        with self.assertRaisesRegex(OrchestraLiveWebError, "missing, foreign, or consumed"):
            self.service.run_preview(request)
        self.assertEqual(
            [("model-0", "MAIN"), ("model-1", "CRITIC")],
            self.fake_invoker.calls,
        )

    def test_web_routes_use_lazy_service_and_do_not_echo_secret(self) -> None:
        with patch("runtime.webapp.get_orchestra_service", return_value=self.service):
            status, created = route_post_payload(
                "/api/provider-connections",
                {
                    "connection_id": "route-connection",
                    "display_name": "Route connection",
                    "api_style": "openai_compatible",
                    "base_url": "https://example.invalid/v1",
                    "api_key": self.API_KEY,
                },
            )
            self.assertEqual(HTTPStatus.CREATED, status)
            self.assertNotIn(self.API_KEY, json.dumps(created, sort_keys=True))
            status, listed = route_get_payload("/api/provider-connections")
            self.assertEqual(HTTPStatus.OK, status)
            self.assertNotIn(self.API_KEY, json.dumps(listed, sort_keys=True))

    def test_sensitive_handler_rejects_wrong_content_type_and_cross_origin(self) -> None:
        for headers, expected in (
            ({"Content-Length": "2"}, HTTPStatus.UNSUPPORTED_MEDIA_TYPE),
            (
                {
                    "Content-Length": "2",
                    "Content-Type": "application/json",
                    "Origin": "https://attacker.invalid",
                    "Host": "127.0.0.1:4311",
                    "Sec-Fetch-Site": "cross-site",
                },
                HTTPStatus.FORBIDDEN,
            ),
        ):
            with self.subTest(expected=expected):
                writes: list[tuple[HTTPStatus, dict[str, object]]] = []
                handler = object.__new__(CodexStyleHandler)
                handler.path = "/api/orchestra/run"
                handler.headers = {"Host": "127.0.0.1:4311", **headers}
                handler.client_address = ("127.0.0.1", 12345)
                handler.rfile = BytesIO(b"{}")
                handler._write_json = lambda status, response: writes.append((status, response))
                CodexStyleHandler.do_POST(handler)
                self.assertEqual(expected, writes[0][0])

    def test_sensitive_handler_rejects_remote_clients_and_dns_rebinding_hosts(self) -> None:
        for client, host in (
            (("198.51.100.10", 12345), "127.0.0.1:4311"),
            (("127.0.0.1", 12345), "attacker.example:4311"),
        ):
            with self.subTest(client=client, host=host):
                writes: list[tuple[HTTPStatus, dict[str, object]]] = []
                handler = object.__new__(CodexStyleHandler)
                handler.path = "/api/orchestra/run"
                handler.headers = {
                    "Host": host,
                    "Content-Length": "2",
                    "Content-Type": "application/json",
                }
                handler.client_address = client
                handler.rfile = BytesIO(b"{}")
                handler._write_json = lambda status, response: writes.append((status, response))
                CodexStyleHandler.do_POST(handler)
                self.assertEqual(HTTPStatus.FORBIDDEN, writes[0][0])

    def test_json_body_limit_fails_before_reading_unbounded_input(self) -> None:
        writes: list[tuple[HTTPStatus, dict[str, object]]] = []
        handler = object.__new__(CodexStyleHandler)
        handler.headers = {"Content-Length": str(256 * 1024 + 1)}
        handler.rfile = BytesIO(b"")
        handler._write_json = lambda status, response: writes.append((status, response))
        self.assertIsNone(CodexStyleHandler._read_json_body(handler))
        self.assertEqual(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, writes[0][0])


if __name__ == "__main__":
    unittest.main()
