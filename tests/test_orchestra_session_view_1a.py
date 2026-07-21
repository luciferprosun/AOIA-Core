from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import FrozenInstanceError, replace
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from runtime.epistemic_orchestra.canonical import exact_text_sha256
from runtime.epistemic_orchestra.live_session import consume_live_stage_authorization
from runtime.epistemic_orchestra.session_view import (
    HUMAN_REVIEW_WARNING,
    OrchestraSessionNotFoundError,
    build_orchestra_session_view,
    serialize_orchestra_session_view,
)
from runtime.providers.orchestra_live_service import (
    OrchestraLiveWebError,
    OrchestraLiveWebService,
)
from runtime.providers.user_connections import UserProviderStore
from runtime.webapp import CodexStyleHandler, route_get_payload


class _MutableClock:
    def __init__(self, start: int = 1_800_000_000) -> None:
        self.value = start

    def __call__(self) -> float:
        return float(self.value)

    def advance(self, seconds: int) -> None:
        self.value += seconds


class _FakeExactInvoker:
    """Deterministic exact-model fake shared by the presentation regressions."""

    def __init__(self, store: UserProviderStore) -> None:
        self.store = store
        self.calls: list[tuple[str, str]] = []
        self.prompts: list[str] = []
        self.fail_role: str | None = None
        self.fail_model_profile_id: str | None = None
        self.responses_by_role: dict[str, str] = {}
        self.responses_by_model: dict[str, str] = {}

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
        self.prompts.append(prompt)
        if (
            binding.operator_role == self.fail_role
            or binding.model_profile_id == self.fail_model_profile_id
        ):
            raise TimeoutError("untrusted secret-bearing provider failure detail")
        response = self.responses_by_model.get(binding.model_profile_id)
        if response is None:
            response = self.responses_by_role.get(binding.operator_role)
        if response is None and binding.operator_role in {"CRITIC", "AUDITOR"}:
            response = json.dumps(
                {"critic_outcome": "NO_MATERIAL_ISSUE_FOUND", "issues": []},
                sort_keys=True,
                separators=(",", ":"),
            )
        if response is None and binding.operator_role == "SYNTHESIZER":
            response = "Non-authoritative synthesized draft for human review."
        if response is None:
            response = "Non-authoritative main draft for human review."
        return SimpleNamespace(
            binding_hash=binding.binding_hash,
            connection_id=binding.connection_id,
            model_profile_id=binding.model_profile_id,
            remote_model_id=binding.remote_model_id,
            response_text=response,
            latency_ms=7,
            trust_status="UNTRUSTED",
            authority_status="NON_AUTHORITATIVE",
            authoritative=False,
            can_approve=False,
            can_write=False,
            can_execute=False,
            can_satisfy_gate=False,
            human_review_required=True,
        )


class _SessionHarness(unittest.TestCase):
    API_KEY = "sk-session-view-configured-secret-material-000001"
    DEFAULT_ROLES = ("MAIN", "CRITIC", "AUDITOR")

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = UserProviderStore(
            self.root / "project",
            state_root=self.root / "state",
            secrets_root=self.root / "secrets",
        )
        self.clock = _MutableClock()
        self.fake_invoker = _FakeExactInvoker(self.store)
        self.service = OrchestraLiveWebService(
            self.root / "project",
            store=self.store,
            exact_invoker=self.fake_invoker,  # type: ignore[arg-type]
            clock=self.clock,
        )
        self._add_connection_and_models(5)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _add_connection_and_models(self, count: int = 5) -> None:
        self.service.create_connection(
            {
                "connection_id": "session-view-connection",
                "display_name": "Session View Connection",
                "api_style": "openai_compatible",
                "base_url": "https://example.invalid/v1",
                "api_key": self.API_KEY,
            }
        )
        for index in range(count):
            self.service.create_model_profile(
                {
                    "model_profile_id": f"session-model-{index}",
                    "connection_id": "session-view-connection",
                    "display_name": f"Session Model {index}",
                    "remote_model_id": f"example/session-model-{index}",
                    "allowed_roles": ["MAIN", "CRITIC", "AUDITOR", "SYNTHESIZER"],
                }
            )

    @staticmethod
    def _selection(
        roles: tuple[str, ...] = DEFAULT_ROLES,
        *,
        reverse: bool = False,
    ) -> list[dict[str, str]]:
        selected = [
            {"model_profile_id": f"session-model-{index}", "role": role}
            for index, role in enumerate(roles)
        ]
        return list(reversed(selected)) if reverse else selected

    def _create_preview(
        self,
        roles: tuple[str, ...] = DEFAULT_ROLES,
        *,
        reverse: bool = False,
        prompt: str = "Produce one bounded draft for explicit human review.",
    ) -> dict[str, object]:
        return self.service.create_preview(
            {
                "source_prompt": prompt,
                "selections": self._selection(roles, reverse=reverse),
                "timeout_seconds": 5,
                "maximum_output_tokens": 64,
            }
        )

    @staticmethod
    def _session_id(preview_payload: dict[str, object]) -> str:
        preview = preview_payload["preview"]
        assert isinstance(preview, dict)
        session_id = preview["orchestra_run_id"]
        assert isinstance(session_id, str)
        return session_id

    def _run_preview(self, preview_payload: dict[str, object]) -> dict[str, object]:
        preview = preview_payload["preview"]
        assert isinstance(preview, dict)
        preview_hash = preview["preview_hash"]
        assert isinstance(preview_hash, str)
        return self.service.run_preview(
            {
                "preview_hash": preview_hash,
                "confirmation_hash": preview_hash,
                "confirmed_preview_hash": preview_hash,
                "explicit_run_action": True,
            }
        )

    def _snapshot(self, preview_payload: dict[str, object]):
        return self.service._session_snapshots[self._session_id(preview_payload)]

    def _view(self, preview_payload: dict[str, object]) -> dict[str, object]:
        return self.service.get_orchestra_session_view(self._session_id(preview_payload))

    def _complete(
        self,
        roles: tuple[str, ...] = DEFAULT_ROLES,
        *,
        responses_by_role: dict[str, str] | None = None,
        responses_by_model: dict[str, str] | None = None,
        reverse: bool = False,
    ):
        if responses_by_role is not None:
            self.fake_invoker.responses_by_role.update(responses_by_role)
        if responses_by_model is not None:
            self.fake_invoker.responses_by_model.update(responses_by_model)
        preview = self._create_preview(roles, reverse=reverse)
        result = self._run_preview(preview)
        self.assertTrue(result["ok"])
        return preview, self._snapshot(preview), self._view(preview)


_SessionViewHarness = _SessionHarness


class OrchestraSessionView1ATests(_SessionHarness):
    def test_same_snapshot_serializes_deterministically_and_records_are_frozen(self) -> None:
        preview = self._create_preview()
        snapshot = self._snapshot(preview)
        first = build_orchestra_session_view(snapshot)
        second = build_orchestra_session_view(snapshot)

        self.assertEqual(first, second)
        self.assertEqual(
            serialize_orchestra_session_view(first),
            serialize_orchestra_session_view(second),
        )
        self.assertEqual(first.session_digest, second.session_digest)
        with self.assertRaises(FrozenInstanceError):
            first.session_state = "COMPLETED"  # type: ignore[misc]
        with self.assertRaises(FrozenInstanceError):
            snapshot.plan_available = False  # type: ignore[misc]

    def test_role_order_is_stable_when_operator_selection_is_reversed(self) -> None:
        ordered = self._create_preview(reverse=False)
        reversed_input = self._create_preview(reverse=True)
        ordered_roles = self._view(ordered)["role_results"]
        reversed_roles = self._view(reversed_input)["role_results"]
        self.assertIsInstance(ordered_roles, list)
        self.assertIsInstance(reversed_roles, list)
        ordered_identity = [
            (item["ordering_index"], item["operator_role"], item["model_profile_id"])
            for item in ordered_roles
        ]
        reversed_identity = [
            (item["ordering_index"], item["operator_role"], item["model_profile_id"])
            for item in reversed_roles
        ]
        self.assertEqual(ordered_identity, reversed_identity)
        self.assertEqual(
            [(0, "MAIN", "session-model-0"), (1, "CRITIC", "session-model-1"), (2, "AUDITOR", "session-model-2")],
            ordered_identity,
        )

    def test_role_order_is_stable_when_completed_results_are_reversed(self) -> None:
        _preview, snapshot, original = self._complete()
        reordered_snapshot = replace(
            snapshot,
            completed_stage_results=tuple(reversed(snapshot.completed_stage_results)),
        )

        rebuilt = build_orchestra_session_view(reordered_snapshot).to_dict()
        self.assertEqual(original["role_results"], rebuilt["role_results"])
        self.assertEqual(original["session_digest"], rebuilt["session_digest"])

    def test_not_executed_and_complete_lifecycle_present_exact_evidence(self) -> None:
        preview = self._create_preview()
        pending_snapshot = self._snapshot(preview)
        pending = self._view(preview)
        self.assertEqual("NOT_EXECUTED", pending["session_state"])
        self.assertTrue(pending["plan_available"])
        self.assertFalse(pending["plan_consumed"])
        self.assertFalse(pending["plan_reusable"])
        self.assertFalse(pending["exact_human_confirmation_recorded"])
        self.assertEqual(0, pending["completed_role_count"])
        self.assertEqual(3, pending["failed_or_incomplete_role_count"])
        self.assertEqual(pending_snapshot.run.run_hash, pending["run_hash"])
        self.assertEqual(
            pending_snapshot.preview.preview_hash,
            pending["live_run_plan_digest"],
        )
        self.assertEqual(
            pending_snapshot.role_selection.role_selection_hash,
            pending["role_selection_digest"],
        )
        self.assertEqual(
            pending_snapshot.run.source_prompt_hash,
            pending["source_prompt_digest"],
        )
        self.assertTrue(
            {
                pending_snapshot.run.run_hash,
                pending_snapshot.preview.preview_hash,
                pending_snapshot.role_selection.role_selection_hash,
                pending_snapshot.run.source_prompt_hash,
            }.issubset(set(pending["evidence_references"]))
        )

        run_result = self._run_preview(preview)
        self.assertTrue(run_result["ok"])
        complete = self._view(preview)
        self.assertEqual("COMPLETED", complete["session_state"])
        self.assertFalse(complete["plan_available"])
        self.assertTrue(complete["plan_consumed"])
        self.assertFalse(complete["plan_reusable"])
        self.assertTrue(complete["exact_human_confirmation_recorded"])
        self.assertTrue(complete["confirmation_is_evidence_only"])
        self.assertEqual(
            self._snapshot(preview).confirmation_hash,
            complete["confirmation_digest"],
        )
        self.assertEqual(3, complete["selected_role_count"])
        self.assertEqual(3, complete["completed_role_count"])
        self.assertEqual(0, complete["failed_or_incomplete_role_count"])
        self.assertEqual("VALID_NON_AUTHORITATIVE", complete["evidence_status"])
        self.assertEqual(["MAIN", "CRITIC", "AUDITOR"], [
            item["operator_role"] for item in complete["role_results"]
        ])
        self.assertEqual([7, 7, 7], [item["latency_ms"] for item in complete["role_results"]])
        completed_snapshot = self._snapshot(preview)
        for index, role_view in enumerate(complete["role_results"]):
            plan = completed_snapshot.preview.planned_calls[index]
            assignment = completed_snapshot.role_selection.assignments[index]
            result = completed_snapshot.completed_stage_results[index]
            expected_references = {
                plan.plan_entry_hash,
                assignment.role_assignment_hash,
                assignment.connection_revision_hash,
                assignment.model_revision_hash,
                result.binding.stage_hash,
                result.binding.binding_hash,
                result.response_hash,
            }
            with self.subTest(index=index, role=role_view["operator_role"]):
                self.assertTrue(
                    expected_references.issubset(set(role_view["evidence_references"]))
                )

    def test_partial_and_failed_provider_sessions_are_retained_without_error_detail(self) -> None:
        self.fake_invoker.fail_role = "CRITIC"
        partial_preview = self._create_preview(("MAIN", "CRITIC", "AUDITOR"))
        partial_result = self._run_preview(partial_preview)
        self.assertFalse(partial_result["ok"])
        partial = self._view(partial_preview)
        self.assertEqual("PARTIAL", partial["session_state"])
        self.assertEqual(1, partial["completed_role_count"])
        self.assertEqual(2, partial["failed_or_incomplete_role_count"])
        self.assertEqual(
            ["COMPLETED", "FAILED", "INCOMPLETE"],
            [item["invocation_status"] for item in partial["role_results"]],
        )
        self.assertNotIn("provider failure detail", json.dumps(partial, sort_keys=True))

        self.fake_invoker.fail_role = "MAIN"
        failed_preview = self._create_preview(("MAIN", "CRITIC"))
        failed_result = self._run_preview(failed_preview)
        self.assertFalse(failed_result["ok"])
        failed = self._view(failed_preview)
        self.assertEqual("FAILED", failed["session_state"])
        self.assertEqual(0, failed["completed_role_count"])
        self.assertEqual(2, failed["failed_or_incomplete_role_count"])
        self.assertEqual("FAILED", failed["role_results"][0]["invocation_status"])
        self.assertFalse(failed["provider_call_permitted"])
        self.assertTrue(failed["human_review_required"])

    def test_read_only_get_does_not_call_provider_mutate_state_or_write_files(self) -> None:
        preview = self._create_preview()
        session_id = self._session_id(preview)
        snapshot = self._snapshot(preview)
        issued_before = dict(self.service._issued_previews)
        snapshots_before = dict(self.service._session_snapshots)
        registry_before = (
            dict(self.service.session_registry._issued_confirmations),
            dict(self.service.session_registry._claimed_confirmations),
            dict(self.service.session_registry._issued_stage_authorizations),
            dict(self.service.session_registry._consumed_stage_authorizations),
        )
        state_before = self.store.config_path.read_bytes()
        secret_path = self.store.secrets_root / "session-view-connection.key"
        secret_before = secret_path.read_bytes()

        with patch.object(
            UserProviderStore,
            "_write_atomic_regular_file",
            side_effect=AssertionError("session GET attempted a filesystem write"),
        ) as write_file:
            first = self.service.get_orchestra_session_view(session_id)
            second = self.service.get_orchestra_session_view(session_id)

        self.assertEqual(first, second)
        self.assertEqual([], self.fake_invoker.calls)
        self.assertEqual(issued_before, self.service._issued_previews)
        self.assertEqual(snapshots_before, self.service._session_snapshots)
        self.assertIs(snapshot, self.service._session_snapshots[session_id])
        self.assertEqual(
            registry_before,
            (
                self.service.session_registry._issued_confirmations,
                self.service.session_registry._claimed_confirmations,
                self.service.session_registry._issued_stage_authorizations,
                self.service.session_registry._consumed_stage_authorizations,
            ),
        )
        self.assertEqual(state_before, self.store.config_path.read_bytes())
        self.assertEqual(
            secret_before,
            secret_path.read_bytes(),
        )
        write_file.assert_not_called()

    def test_expired_view_is_deterministic_and_does_not_refresh_or_consume_plan(self) -> None:
        preview = self._create_preview()
        snapshot_before = self._snapshot(preview)
        expires = snapshot_before.preview.expires_at_epoch
        self.clock.advance(301)

        first = self._view(preview)
        second = self._view(preview)
        self.assertEqual(first, second)
        self.assertEqual("EXPIRED", first["session_state"])
        self.assertEqual("FAIL_CLOSED", first["evidence_status"])
        self.assertEqual("FAIL_CLOSED", first["audit_result"]["audit_status"])
        self.assertIn(
            "LIVE_RUN_PLAN_EXPIRED",
            first["audit_result"]["stale_or_malformed_evidence"],
        )
        self.assertEqual(expires, first["updated_at_epoch"])
        self.assertEqual(expires, first["plan_expiration_epoch"])
        self.assertFalse(first["plan_available"])
        self.assertFalse(first["plan_consumed"])
        self.assertFalse(first["plan_reusable"])
        self.assertFalse(first["exact_human_confirmation_recorded"])
        self.assertIs(snapshot_before, self._snapshot(preview))
        self.assertEqual("NOT_EXECUTED", snapshot_before.session_state)
        self.assertTrue(snapshot_before.plan_available)
        self.assertEqual([], self.fake_invoker.calls)
        with self.assertRaisesRegex(OrchestraLiveWebError, "expired"):
            self._run_preview(preview)
        self.assertEqual([], self.fake_invoker.calls)

    def test_consumed_session_view_cannot_replay_confirmation_or_provider_calls(self) -> None:
        preview, _snapshot, first = self._complete(("MAIN", "CRITIC"))
        calls_after_run = list(self.fake_invoker.calls)
        second = self._view(preview)
        self.assertEqual(first, second)
        self.assertEqual(calls_after_run, self.fake_invoker.calls)
        with self.assertRaisesRegex(OrchestraLiveWebError, "missing, foreign, or consumed"):
            self._run_preview(preview)
        self.assertEqual(calls_after_run, self.fake_invoker.calls)

    def test_provider_display_redacts_secret_and_control_text_without_secret_digest(self) -> None:
        secret = "sk-or-v1-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnop"
        basic_credential = "dXNlcjpwYXNzd29yZA=="
        opaque_token = "AbCdEf0123456789_ZyxWvu9876543210-QrStUvWxYz"
        path_opaque_token = "AbCdEf0123456789ZYXWVUT9876543210QrStUvWxYz"
        unsafe_response = (
            f"Draft api_key={secret}\n"
            f"Authorization: Basic {basic_credential}\n"
            f"opaque={opaque_token}\n"
            f"path=/safe/path/{path_opaque_token}\x1b[31m untrusted"
        )
        preview, _snapshot, view = self._complete(
            ("MAIN", "CRITIC", "AUDITOR", "SYNTHESIZER"),
            responses_by_role={"MAIN": unsafe_response},
        )
        serialized = json.dumps(view, ensure_ascii=False, sort_keys=True)
        self.assertNotIn(secret, serialized)
        self.assertNotIn(basic_credential, serialized)
        self.assertNotIn(opaque_token, serialized)
        self.assertNotIn(path_opaque_token, serialized)
        self.assertNotIn("\x1b", serialized)
        self.assertNotIn(exact_text_sha256(unsafe_response), serialized)
        snapshot = self._snapshot(preview)
        for downstream in snapshot.completed_stage_results[1:]:
            self.assertNotIn(downstream.binding.binding_hash, serialized)
        main = view["role_results"][0]
        self.assertTrue(main["redaction_or_sanitization_applied"])
        self.assertIsNone(main["response_digest"])
        self.assertIn("[REDACTED_PROVIDER_SECRET]", main["redacted_provider_response"])
        self.assertIn(
            "PROVIDER_DISPLAY_REDACTED_OR_SANITIZED",
            view["audit_result"]["redaction_warnings"],
        )
        self.assertIn(
            "DOWNSTREAM_EVIDENCE_DIGESTS_WITHHELD_BY_REDACTION",
            view["audit_result"]["redaction_warnings"],
        )
        for downstream_view in view["role_results"][1:]:
            self.assertIsNone(downstream_view["response_digest"])
            self.assertIsNone(downstream_view["stage_hash"])
            self.assertTrue(downstream_view["redaction_or_sanitization_applied"])
        self.assertIsNone(view["critic_results"][0]["report_digest"])
        self.assertIsNone(view["critic_results"][0]["critic_output_digest"])
        self.assertIsNone(view["final_draft_digest"])
        self.assertTrue(view["final_draft_redaction_or_sanitization_applied"])
        self.assertEqual(self._session_id(preview), view["session_id"])

    def test_configured_credential_from_provider_is_withheld_from_session_view(self) -> None:
        self.fake_invoker.responses_by_role["MAIN"] = self.API_KEY
        preview = self._create_preview(("MAIN", "CRITIC"))
        with self.assertRaisesRegex(
            OrchestraLiveWebError,
            "configured credential",
        ):
            self._run_preview(preview)

        view = self._view(preview)
        serialized = json.dumps(view, ensure_ascii=False, sort_keys=True)
        self.assertNotIn(self.API_KEY, serialized)
        self.assertEqual("FAILED", view["session_state"])
        self.assertEqual(0, view["completed_role_count"])
        self.assertIn(
            "SESSION_OUTPUT_WITHHELD_BY_CREDENTIAL_BOUNDARY",
            view["audit_result"]["redaction_warnings"],
        )

    def test_mismatched_completed_evidence_is_visible_and_fails_closed(self) -> None:
        preview, snapshot, _view = self._complete(("MAIN", "CRITIC"))
        mismatched = replace(
            snapshot,
            completed_stage_results=(object(),),
            session_result=None,
        )
        self.service._session_snapshots[self._session_id(preview)] = mismatched

        view = self._view(preview)
        self.assertEqual("FAIL_CLOSED", view["evidence_status"])
        self.assertEqual("FAIL_CLOSED", view["audit_result"]["audit_status"])
        self.assertIn(
            "RESULT_TYPE_MISMATCH",
            view["audit_result"]["hash_mismatches"],
        )
        self.assertTrue(all(
            item["response_status"] != "AVAILABLE" for item in view["role_results"]
        ))
        self.assertFalse(view["approval_permitted"])
        self.assertFalse(view["gate_mutation_permitted"])

    def test_tampered_stage_binding_self_hash_fails_closed(self) -> None:
        preview, snapshot, _view = self._complete(("MAIN", "CRITIC"))
        binding = snapshot.completed_stage_results[1].binding
        object.__setattr__(binding, "binding_hash", "0" * 64)

        view = self._view(preview)
        self.assertEqual("FAIL_CLOSED", view["evidence_status"])
        self.assertIn(
            "RESULT_BINDING_MISMATCH",
            view["audit_result"]["hash_mismatches"],
        )
        self.assertEqual(
            "EVIDENCE_MISMATCH",
            view["role_results"][1]["invocation_status"],
        )
        self.assertNotIn("0" * 64, json.dumps(view, sort_keys=True))

    def test_dynamic_get_route_returns_200_400_and_404_without_provider_calls(self) -> None:
        preview = self._create_preview()
        session_id = self._session_id(preview)
        with patch("runtime.webapp.get_orchestra_service", return_value=self.service):
            status, payload = route_get_payload(
                f"/api/orchestra/sessions/{session_id}"
            )
            self.assertEqual(HTTPStatus.OK, status)
            self.assertEqual(session_id, payload["session_id"])

            for malformed in (
                "/api/orchestra/sessions",
                "/api/orchestra/sessions/",
                "/api/orchestra/sessions/a/b",
                "/api/orchestra/sessions/%2e%2e",
                "/api/orchestra/sessions/contains%20space",
            ):
                with self.subTest(malformed=malformed):
                    bad_status, bad_payload = route_get_payload(malformed)
                    self.assertEqual(HTTPStatus.BAD_REQUEST, bad_status)
                    self.assertEqual("session identifier is malformed", bad_payload["error"])

            missing_status, missing = route_get_payload(
                "/api/orchestra/sessions/orchestra-web-unknown"
            )
            self.assertEqual(HTTPStatus.NOT_FOUND, missing_status)
            self.assertNotIn("orchestra-web-unknown", json.dumps(missing))
        self.assertEqual([], self.fake_invoker.calls)

    def test_dynamic_get_handler_requires_loopback_client_and_host(self) -> None:
        preview = self._create_preview()
        path = f"/api/orchestra/sessions/{self._session_id(preview)}"
        with patch("runtime.webapp.get_orchestra_service", return_value=self.service):
            allowed_writes: list[tuple[HTTPStatus, dict[str, object]]] = []
            allowed = object.__new__(CodexStyleHandler)
            allowed.path = path
            allowed.headers = {"Host": "127.0.0.1:4311"}
            allowed.client_address = ("127.0.0.1", 12345)
            allowed._write_json = lambda status, payload: allowed_writes.append((status, payload))
            CodexStyleHandler.do_GET(allowed)
            self.assertEqual(HTTPStatus.OK, allowed_writes[0][0])

            for client, host in (
                (("198.51.100.20", 12345), "127.0.0.1:4311"),
                (("127.0.0.1", 12345), "attacker.example:4311"),
            ):
                with self.subTest(client=client, host=host):
                    writes: list[tuple[HTTPStatus, dict[str, object]]] = []
                    handler = object.__new__(CodexStyleHandler)
                    handler.path = path
                    handler.headers = {"Host": host}
                    handler.client_address = client
                    handler._write_json = lambda status, payload: writes.append((status, payload))
                    CodexStyleHandler.do_GET(handler)
                    self.assertEqual(HTTPStatus.FORBIDDEN, writes[0][0])
        self.assertEqual([], self.fake_invoker.calls)

    def test_ui_contains_persistent_warning_and_only_explicit_non_polling_load(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        markup = (repository / "web" / "index.html").read_text(encoding="utf-8")
        script = (repository / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn(HUMAN_REVIEW_WARNING, markup)
        self.assertIn("id=\"load-orchestra-session\"", markup)
        self.assertIn(
            'elements.loadOrchestraSession.addEventListener("click", loadOrchestraSessionView);',
            script,
        )
        self.assertEqual(2, script.count("loadOrchestraSessionView"))
        self.assertNotIn("setInterval(", script)
        self.assertIn("role_results", script)
        self.assertIn("textContent", script)
        self.assertIn("function clearOrchestraSessionView()", script)
        self.assertIn(
            "async function loadOrchestraSessionView() {\n  clearOrchestraSessionView();",
            script,
        )
        self.assertIn("orchestraSessionRoleTableBody.replaceChildren()", script)
        self.assertIn("orchestraSessionProviderResults.replaceChildren()", script)
        self.assertIn("orchestraSessionCriticResults.replaceChildren()", script)
        self.assertIn(
            'elements.orchestraSessionId.addEventListener("input", () => {',
            script,
        )
        self.assertIn(
            "clearOrchestraSessionView();\n    elements.orchestraSessionId.value",
            script,
        )
        run_renderer = script.split("async function runOrchestra()", 1)[1].split(
            "function renderSafeJson", 1
        )[0]
        self.assertIn("clearOrchestraSessionView();", run_renderer)
        self.assertIn("Session lifecycle changed", run_renderer)
        for field in (
            "run_hash",
            "role_selection_digest",
            "source_prompt_digest",
            "confirmation_digest",
            "evidence_references",
            "safety_warnings",
            "authority_status",
        ):
            with self.subTest(field=field):
                self.assertIn(f"{field}: payload.{field}", script)

    def test_unknown_service_session_raises_safe_not_found_error(self) -> None:
        with self.assertRaises(OrchestraSessionNotFoundError) as caught:
            self.service.get_orchestra_session_view("orchestra-web-unknown")
        self.assertNotIn(self.API_KEY, str(caught.exception))


if __name__ == "__main__":
    unittest.main()
