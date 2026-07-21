from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import traceback
import unittest
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from runtime.epistemic_orchestra.canonical import canonical_sha256
from runtime.epistemic_orchestra.contracts import build_epistemic_stage_contract
from runtime.epistemic_orchestra.live_run_preview import build_live_run_preview
from runtime.epistemic_orchestra.live_session import (
    LIVE_STAGE_BINDING_SCHEMA_VERSION,
    LiveSessionUseRegistry,
    LiveStageInvocationBinding,
)
from runtime.epistemic_orchestra.role_binding import (
    build_model_role_assignment,
    build_orchestra_role_selection,
)
from runtime.providers.exact_invocation import (
    ExactInvocationError,
    ExactProviderInvoker,
    consume_gateway_transport_authorization,
    consume_gateway_transport_receipt,
)
from runtime.providers.openai_compatible import (
    OpenAICompatibleProvider,
    _NoRedirectHandler,
    _open_without_redirects,
)
from runtime.providers.user_connections import UserProviderStore


class _Response:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, maximum: int = -1) -> bytes:
        return self.payload if maximum < 0 else self.payload[:maximum]


class OrchestraExactInvocation1ATests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.secret = "sk-test-exact-provider-secret-123456"
        self.store = UserProviderStore(
            root / "project",
            state_root=root / "state",
            secrets_root=root / "secrets",
        )
        self.connection = self.store.create_connection(
            connection_id="exact-connection",
            display_name="Exact Connection",
            api_style="openai_compatible",
            base_url="https://models.example.test/v1",
            credential_reference="exact-credential",
            created_at="operator-time",
            api_key=self.secret,
        )
        self.main_profile = self.store.create_model_profile(
            model_profile_id="exact-main",
            connection_id=self.connection.connection_id,
            display_name="Exact Main",
            remote_model_id="vendor/exact-main",
            allowed_roles=("MAIN",),
        )
        self.critic_profile = self.store.create_model_profile(
            model_profile_id="exact-critic",
            connection_id=self.connection.connection_id,
            display_name="Exact Critic",
            remote_model_id="vendor/exact-critic",
            allowed_roles=("CRITIC",),
        )

    def make_main_authorization(self):
        assignments = (
            build_model_role_assignment(
                ordinal=0,
                connection=self.connection,
                model_profile=self.main_profile,
                role="MAIN",
            ),
            build_model_role_assignment(
                ordinal=1,
                connection=self.connection,
                model_profile=self.critic_profile,
                role="CRITIC",
            ),
        )
        selection = build_orchestra_role_selection(assignments)
        run, preview = build_live_run_preview(
            orchestra_run_id="exact-run-1",
            source_prompt="Exact human prompt.",
            role_selection=selection,
            timeout_seconds=7,
            maximum_output_tokens=64,
            expires_at_epoch=200,
        )
        registry = LiveSessionUseRegistry()
        confirmation = registry.issue_confirmation(
            preview=preview,
            confirmed_preview_hash=preview.preview_hash,
            explicit_run_action=True,
            issued_at_epoch=100,
        )
        registry.claim_confirmation(
            confirmation,
            preview=preview,
            run=run,
            role_selection=selection,
            current_epoch=100,
        )
        stage = build_epistemic_stage_contract(
            run=run,
            stage_index=0,
            source_revision_id=f"source-{run.source_prompt_hash[:24]}",
            source_revision_hash=run.source_prompt_hash,
        )
        plan = preview.planned_calls[0]
        binding = LiveStageInvocationBinding(
            schema_version=LIVE_STAGE_BINDING_SCHEMA_VERSION,
            orchestra_run_id=run.run_id,
            run_hash=run.run_hash,
            stage_id=stage.stage_id,
            stage_hash=stage.stage_hash,
            connection_id=assignments[0].connection_id,
            connection_revision_hash=assignments[0].connection_revision_hash,
            model_profile_id=assignments[0].model_profile_id,
            model_revision_hash=assignments[0].model_revision_hash,
            remote_model_id=assignments[0].remote_model_id,
            operator_role=assignments[0].role,
            role_assignment_hash=assignments[0].role_assignment_hash,
            source_prompt_hash=run.source_prompt_hash,
            parent_response_hash=canonical_sha256(
                {
                    "domain": "orchestra-main-parent-response-1a",
                    "sentinel": "NO_PARENT_RESPONSE",
                }
            ),
            plan_entry_hash=plan.plan_entry_hash,
            provider_prompt_hash=run.source_prompt_hash,
            maximum_output_tokens=plan.maximum_output_tokens,
            timeout_seconds=plan.timeout_seconds,
        )
        authorization = registry.issue_stage_authorization(
            confirmation,
            binding,
            stage=stage,
            call_index=0,
        )
        return authorization, binding

    @staticmethod
    def consuming_gateway(calls: list[dict], *, response_text: str = "exact result"):
        def gateway(**kwargs):
            calls.append(kwargs)
            material = {
                key: value
                for key, value in kwargs.items()
                if key not in {"api_key", "transport_authorization"}
            }
            receipt = consume_gateway_transport_authorization(
                kwargs["transport_authorization"],
                **material,
            )
            consume_gateway_transport_receipt(receipt, **material)
            return SimpleNamespace(
                connection_id=kwargs["connection_id"],
                model_profile_id=kwargs["model_profile_id"],
                remote_model_id=kwargs["remote_model_id"],
                response_text=response_text,
                trust_status="UNTRUSTED",
                authority_status="NON_AUTHORITATIVE",
                authoritative=False,
                can_approve=False,
                can_write=False,
                can_execute=False,
                can_satisfy_gate=False,
            )

        return gateway

    def test_exact_selected_model_is_invoked_once_without_fallback_or_retry(self) -> None:
        calls: list[dict] = []
        invoker = ExactProviderInvoker(
            self.store,
            gateway_call=self.consuming_gateway(calls),
            monotonic=iter((1.0, 1.125)).__next__,
        )
        authorization, binding = self.make_main_authorization()
        result = invoker.invoke_exact(
            stage_authorization=authorization,
            binding=binding,
            prompt="Exact human prompt.",
            max_tokens=64,
            timeout_seconds=7,
        )
        self.assertEqual("vendor/exact-main", result.remote_model_id)
        self.assertEqual(1, len(calls))
        self.assertEqual("vendor/exact-main", calls[0]["remote_model_id"])
        self.assertFalse(result.automatic_fallback_used)
        self.assertFalse(result.automatic_retry_used)
        self.assertFalse(result.authoritative)
        self.assertFalse(result.can_satisfy_gate)
        self.assertEqual({}, invoker._transport_registry._issued)
        self.assertEqual({}, invoker._transport_registry._authorization_receipts)
        self.assertEqual({}, invoker._transport_registry._receipts)
        self.assertEqual({}, invoker._transport_registry._consumed_receipts)

    def test_environment_flag_alone_cannot_authorize_exact_call(self) -> None:
        calls: list[dict] = []
        invoker = ExactProviderInvoker(self.store, gateway_call=self.consuming_gateway(calls))
        _authorization, binding = self.make_main_authorization()
        with patch.dict(os.environ, {"AOIA_PROVIDER_CALLS_ENABLED": "1"}, clear=False):
            with self.assertRaisesRegex(Exception, "authorization"):
                invoker.invoke_exact(
                    stage_authorization=object(),
                    binding=binding,
                    prompt="Exact human prompt.",
                    max_tokens=64,
                    timeout_seconds=7,
                )
        self.assertEqual([], calls)

    def test_changed_model_revision_fails_before_gateway_and_consumes_stage(self) -> None:
        calls: list[dict] = []
        invoker = ExactProviderInvoker(self.store, gateway_call=self.consuming_gateway(calls))
        authorization, binding = self.make_main_authorization()
        self.store.disable_model_profile(self.main_profile.model_profile_id)
        with self.assertRaisesRegex(ExactInvocationError, "disabled model"):
            invoker.invoke_exact(
                stage_authorization=authorization,
                binding=binding,
                prompt="Exact human prompt.",
                max_tokens=64,
                timeout_seconds=7,
            )
        with self.assertRaisesRegex(Exception, "already been consumed"):
            invoker.invoke_exact(
                stage_authorization=authorization,
                binding=binding,
                prompt="Exact human prompt.",
                max_tokens=64,
                timeout_seconds=7,
            )
        self.assertEqual([], calls)

    def test_missing_credential_blocks_before_gateway(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        missing_store = UserProviderStore(
            root / "project",
            state_root=root / "state",
            secrets_root=root / "secrets",
        )
        connection = missing_store.create_connection(
            connection_id="missing-connection",
            display_name="Missing Connection",
            api_style="openai_compatible",
            base_url="https://missing.example.test/v1",
            credential_reference="missing-key",
            created_at="operator-time",
        )
        profile = missing_store.create_model_profile(
            model_profile_id="missing-main",
            connection_id=connection.connection_id,
            display_name="Missing Main",
            remote_model_id="vendor/missing-main",
            allowed_roles=("MAIN",),
        )
        self.assertEqual("missing", missing_store.credential_status(connection.credential_reference))
        self.assertNotIn("api_key", json.dumps(connection.to_dict()))
        self.assertEqual("vendor/missing-main", profile.remote_model_id)
        calls: list[dict] = []
        invoker = ExactProviderInvoker(
            missing_store,
            gateway_call=self.consuming_gateway(calls),
        )
        authorization = invoker.authorize_connection_test(
            connection_id=connection.connection_id,
            model_profile_id=profile.model_profile_id,
            explicit_operator_action=True,
            issued_at_epoch=100,
            expires_at_epoch=160,
        )
        result = invoker.test_connection(authorization, current_epoch=100)
        self.assertFalse(result.success)
        self.assertEqual("", result.response_preview)
        self.assertEqual([], calls)

    def test_connection_test_requires_explicit_bool_and_calls_once(self) -> None:
        calls: list[dict] = []
        invoker = ExactProviderInvoker(
            self.store,
            gateway_call=self.consuming_gateway(calls, response_text="AOIA_CONNECTION_OK"),
            monotonic=iter((1.0, 1.025)).__next__,
        )
        with self.assertRaisesRegex(ExactInvocationError, "explicit operator"):
            invoker.authorize_connection_test(
                connection_id=self.connection.connection_id,
                model_profile_id=self.main_profile.model_profile_id,
                explicit_operator_action="true",  # type: ignore[arg-type]
                issued_at_epoch=100,
                expires_at_epoch=160,
            )
        authorization = invoker.authorize_connection_test(
            connection_id=self.connection.connection_id,
            model_profile_id=self.main_profile.model_profile_id,
            explicit_operator_action=True,
            issued_at_epoch=100,
            expires_at_epoch=160,
        )
        result = invoker.test_connection(authorization, current_epoch=100)
        self.assertTrue(result.success)
        self.assertEqual("AOIA_CONNECTION_OK", result.response_preview)
        self.assertEqual(1, len(calls))
        with self.assertRaisesRegex(ExactInvocationError, "foreign or consumed"):
            invoker.test_connection(authorization, current_epoch=100)

    def test_transport_authorization_rejects_alternate_endpoint_and_style(self) -> None:
        calls: list[dict] = []

        def malicious_gateway(**kwargs):
            calls.append(kwargs)
            material = {
                key: value
                for key, value in kwargs.items()
                if key not in {"api_key", "transport_authorization"}
            }
            material["base_url"] = "https://attacker.example.test/v1"
            return consume_gateway_transport_authorization(
                kwargs["transport_authorization"],
                **material,
            )

        invoker = ExactProviderInvoker(self.store, gateway_call=malicious_gateway)
        authorization, binding = self.make_main_authorization()
        with self.assertRaisesRegex(ExactInvocationError, "transport inputs differ"):
            invoker.invoke_exact(
                stage_authorization=authorization,
                binding=binding,
                prompt="Exact human prompt.",
                max_tokens=64,
                timeout_seconds=7,
            )
        self.assertEqual(1, len(calls))

    def test_timeout_failure_is_single_attempt_and_redacts_secret(self) -> None:
        calls: list[dict] = []

        def failing_gateway(**kwargs):
            calls.append(kwargs)
            raise TimeoutError(f"timeout with {kwargs['api_key']}")

        invoker = ExactProviderInvoker(self.store, gateway_call=failing_gateway)
        authorization, binding = self.make_main_authorization()
        with self.assertRaises(ExactInvocationError) as caught:
            invoker.invoke_exact(
                stage_authorization=authorization,
                binding=binding,
                prompt="Exact human prompt.",
                max_tokens=64,
                timeout_seconds=7,
            )
        self.assertEqual(1, len(calls))
        self.assertNotIn(self.secret, str(caught.exception))

    def test_configured_key_in_prompt_is_blocked_before_gateway(self) -> None:
        calls: list[dict] = []
        invoker = ExactProviderInvoker(
            self.store,
            gateway_call=self.consuming_gateway(calls),
        )
        with self.assertRaisesRegex(ExactInvocationError, "credential"):
            invoker._call_once(
                purpose="orchestra_live_stage",
                connection=self.connection,
                model_profile_id=self.main_profile.model_profile_id,
                model_revision_hash=self.main_profile.model_revision_hash,
                remote_model_id=self.main_profile.remote_model_id,
                prompt=f"Do not transmit {self.secret}",
                max_tokens=64,
                timeout_seconds=7,
                binding_hash="0" * 64,
            )
        self.assertEqual([], calls)

    def test_gateway_secret_is_absent_from_formatted_traceback(self) -> None:
        captured_key = self.secret

        def failing_gateway(**kwargs):
            raise RuntimeError(f"provider echoed captured credential {captured_key}")

        invoker = ExactProviderInvoker(self.store, gateway_call=failing_gateway)
        authorization, binding = self.make_main_authorization()
        try:
            invoker.invoke_exact(
                stage_authorization=authorization,
                binding=binding,
                prompt="Exact human prompt.",
                max_tokens=64,
                timeout_seconds=7,
            )
        except ExactInvocationError as error:
            formatted = "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
        else:  # pragma: no cover - assertion path
            self.fail("gateway failure should fail closed")

        self.assertNotIn(captured_key, formatted)
        self.assertIn("REDACTED", formatted)

    def test_gateway_must_consume_transport_receipt(self) -> None:
        def bypass_gateway(**kwargs):
            return SimpleNamespace(
                connection_id=kwargs["connection_id"],
                model_profile_id=kwargs["model_profile_id"],
                remote_model_id=kwargs["remote_model_id"],
                response_text="bypass",
                trust_status="UNTRUSTED",
                authority_status="NON_AUTHORITATIVE",
                authoritative=False,
                can_approve=False,
                can_write=False,
                can_execute=False,
                can_satisfy_gate=False,
            )

        invoker = ExactProviderInvoker(self.store, gateway_call=bypass_gateway)
        authorization, binding = self.make_main_authorization()
        with self.assertRaisesRegex(ExactInvocationError, "did not consume"):
            invoker.invoke_exact(
                stage_authorization=authorization,
                binding=binding,
                prompt="Exact human prompt.",
                max_tokens=64,
                timeout_seconds=7,
            )

    def test_prior_identical_call_cannot_cover_a_later_receipt_bypass(self) -> None:
        calls = 0

        def first_consumes_second_bypasses(**kwargs):
            nonlocal calls
            calls += 1
            material = {
                key: value
                for key, value in kwargs.items()
                if key not in {"api_key", "transport_authorization"}
            }
            if calls == 1:
                receipt = consume_gateway_transport_authorization(
                    kwargs["transport_authorization"],
                    **material,
                )
                consume_gateway_transport_receipt(receipt, **material)
            return SimpleNamespace(
                connection_id=kwargs["connection_id"],
                model_profile_id=kwargs["model_profile_id"],
                remote_model_id=kwargs["remote_model_id"],
                response_text="exact result",
                trust_status="UNTRUSTED",
                authority_status="NON_AUTHORITATIVE",
                authoritative=False,
                can_approve=False,
                can_write=False,
                can_execute=False,
                can_satisfy_gate=False,
            )

        invoker = ExactProviderInvoker(
            self.store,
            gateway_call=first_consumes_second_bypasses,
        )
        first_authorization, first_binding = self.make_main_authorization()
        invoker.invoke_exact(
            stage_authorization=first_authorization,
            binding=first_binding,
            prompt="Exact human prompt.",
            max_tokens=64,
            timeout_seconds=7,
        )
        second_authorization, second_binding = self.make_main_authorization()
        with self.assertRaisesRegex(ExactInvocationError, "did not consume"):
            invoker.invoke_exact(
                stage_authorization=second_authorization,
                binding=second_binding,
                prompt="Exact human prompt.",
                max_tokens=64,
                timeout_seconds=7,
            )
        self.assertEqual(2, calls)

    def test_direct_low_level_adapter_call_is_blocked_before_network(self) -> None:
        provider = OpenAICompatibleProvider(
            provider="unregistered-exact-test",
            api_key=self.secret,
            model="vendor/exact-main",
            base_url="https://models.example.test/v1",
        )
        with patch("runtime.providers.openai_compatible._open_without_redirects") as network:
            with self.assertRaisesRegex(RuntimeError, "provider registry"):
                provider._request_once(
                    "Exact human prompt.",
                    max_tokens=64,
                    timeout_seconds=7,
                )
        network.assert_not_called()

    def test_exact_redirect_handler_refuses_redirects(self) -> None:
        handler = _NoRedirectHandler()
        self.assertIsNone(handler.redirect_request(None, None, 302, "Found", {}, "https://other.test"))

    def test_absolute_deadline_blocks_request_bytes_after_late_connect(self) -> None:
        class _Connection:
            sock = None

            def __init__(self) -> None:
                self.requests: list[tuple] = []
                self.closed = False

            def connect(self) -> None:
                return None

            def request(self, *args, **kwargs) -> None:
                self.requests.append((args, kwargs))

            def close(self) -> None:
                self.closed = True

        class _Timer:
            daemon = False

            def start(self) -> None:
                return None

            def cancel(self) -> None:
                return None

        connection = _Connection()
        request = urllib.request.Request(
            "https://models.example.test/v1/chat/completions",
            data=b"{}",
            method="POST",
        )
        with (
            patch(
                "runtime.providers.openai_compatible.http.client.HTTPSConnection",
                return_value=connection,
            ),
            patch(
                "runtime.providers.openai_compatible.threading.Timer",
                return_value=_Timer(),
            ),
            patch(
                "runtime.providers.openai_compatible.time.monotonic",
                side_effect=(100.0, 111.0),
            ),
        ):
            with self.assertRaisesRegex(TimeoutError, "absolute deadline"):
                _open_without_redirects(request, timeout_seconds=10)
        self.assertEqual([], connection.requests)
        self.assertTrue(connection.closed)

    def test_stalled_dns_connect_is_wall_time_bounded_and_never_requests(self) -> None:
        connect_entered = threading.Event()
        release_connect = threading.Event()
        connect_returned = threading.Event()

        class _StalledDNSConnection:
            sock = None

            def __init__(self) -> None:
                self.requests: list[tuple] = []
                self.closed = threading.Event()

            def connect(self) -> None:
                connect_entered.set()
                release_connect.wait(2)
                connect_returned.set()

            def request(self, *args, **kwargs) -> None:
                self.requests.append((args, kwargs))

            def close(self) -> None:
                self.closed.set()

        connection = _StalledDNSConnection()
        request = urllib.request.Request(
            "https://models.example.test/v1/chat/completions",
            data=b"{}",
            method="POST",
        )
        started = time.monotonic()
        try:
            with patch(
                "runtime.providers.openai_compatible.http.client.HTTPSConnection",
                return_value=connection,
            ):
                with self.assertRaisesRegex(TimeoutError, "absolute deadline"):
                    _open_without_redirects(request, timeout_seconds=0.05)
            elapsed = time.monotonic() - started
            self.assertTrue(connect_entered.is_set())
            self.assertLess(elapsed, 0.5)
            self.assertEqual([], connection.requests)
            self.assertTrue(connection.closed.is_set())
        finally:
            release_connect.set()

        self.assertTrue(connect_returned.wait(1))
        self.assertEqual([], connection.requests)
        self.assertTrue(connection.closed.is_set())

    def test_deadline_guard_forbids_implicit_reconnect_and_late_send(self) -> None:
        class _Socket:
            def settimeout(self, value: float) -> None:
                return None

        class _Connection:
            def __init__(self) -> None:
                self.sock = _Socket()
                self.sent: list[bytes] = []
                self.connect_calls = 0

            def connect(self) -> None:
                self.connect_calls += 1

            def send(self, data: bytes) -> None:
                self.sent.append(data)

            def request(self, method, target, *, body, headers) -> None:
                self.send(body)

            def close(self) -> None:
                self.sock = None

        class _Timer:
            daemon = False

            def start(self) -> None:
                return None

            def cancel(self) -> None:
                return None

        connection = _Connection()
        request = urllib.request.Request(
            "https://models.example.test/v1/chat/completions",
            data=b"paid-request-bytes",
            method="POST",
        )
        with (
            patch(
                "runtime.providers.openai_compatible.http.client.HTTPSConnection",
                return_value=connection,
            ),
            patch(
                "runtime.providers.openai_compatible.threading.Timer",
                return_value=_Timer(),
            ),
            patch(
                "runtime.providers.openai_compatible.time.monotonic",
                side_effect=(100.0, 100.0, 100.0, 100.0, 111.0),
            ),
        ):
            with self.assertRaisesRegex(TimeoutError, "absolute deadline"):
                _open_without_redirects(request, timeout_seconds=10)

        self.assertEqual(1, connection.connect_calls)
        self.assertEqual([], connection.sent)

    def test_connect_worker_capacity_saturation_fails_before_connect(self) -> None:
        class _NoSlot:
            def acquire(self, *, blocking: bool) -> bool:
                self.blocking = blocking
                return False

            def release(self) -> None:  # pragma: no cover - must not release
                raise AssertionError("unacquired slot must not be released")

        class _Connection:
            sock = None

            def __init__(self) -> None:
                self.connect_calls = 0
                self.requests: list[tuple] = []

            def connect(self) -> None:
                self.connect_calls += 1

            def request(self, *args, **kwargs) -> None:
                self.requests.append((args, kwargs))

            def close(self) -> None:
                return None

        slot = _NoSlot()
        connection = _Connection()
        request = urllib.request.Request(
            "https://models.example.test/v1/chat/completions",
            data=b"{}",
            method="POST",
        )
        with (
            patch(
                "runtime.providers.openai_compatible._CONNECT_WORKER_SLOTS",
                slot,
            ),
            patch(
                "runtime.providers.openai_compatible.http.client.HTTPSConnection",
                return_value=connection,
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "capacity is exhausted"):
                _open_without_redirects(request, timeout_seconds=1)

        self.assertFalse(slot.blocking)
        self.assertEqual(0, connection.connect_calls)
        self.assertEqual([], connection.requests)

    def test_real_adapter_path_reads_once_with_bound_size(self) -> None:
        payload = json.dumps(
            {"choices": [{"message": {"content": "adapter result"}, "finish_reason": "stop"}]}
        ).encode("utf-8")
        invoker = ExactProviderInvoker(self.store)
        authorization, binding = self.make_main_authorization()
        with (
            patch.dict(os.environ, {"AOIA_PROVIDER_CALLS_ENABLED": "1"}, clear=False),
            patch(
                "runtime.providers.openai_compatible._open_without_redirects",
                return_value=_Response(payload),
            ) as network,
        ):
            result = invoker.invoke_exact(
                stage_authorization=authorization,
                binding=binding,
                prompt="Exact human prompt.",
                max_tokens=64,
                timeout_seconds=7,
            )
        self.assertEqual("adapter result", result.response_text)
        network.assert_called_once()

    def test_oversized_exact_response_fails_closed_after_one_read(self) -> None:
        invoker = ExactProviderInvoker(self.store)
        authorization, binding = self.make_main_authorization()
        oversized = b"{" + b"A" * 1_000_100
        with (
            patch.dict(os.environ, {"AOIA_PROVIDER_CALLS_ENABLED": "1"}, clear=False),
            patch(
                "runtime.providers.openai_compatible._open_without_redirects",
                return_value=_Response(oversized),
            ) as network,
        ):
            with self.assertRaisesRegex(ExactInvocationError, "bounded byte limit"):
                invoker.invoke_exact(
                    stage_authorization=authorization,
                    binding=binding,
                    prompt="Exact human prompt.",
                    max_tokens=64,
                    timeout_seconds=7,
                )
        network.assert_called_once()

    def test_malformed_schema_and_provider_controlled_finish_reason_fail_closed(self) -> None:
        for payload in (
            {"unexpected": []},
            {
                "choices": [
                    {
                        "message": {"content": "text"},
                        "finish_reason": "Bearer secret-bearing-metadata",
                    }
                ]
            },
        ):
            with self.subTest(payload=payload):
                invoker = ExactProviderInvoker(self.store)
                authorization, binding = self.make_main_authorization()
                with (
                    patch.dict(os.environ, {"AOIA_PROVIDER_CALLS_ENABLED": "1"}, clear=False),
                    patch(
                        "runtime.providers.openai_compatible._open_without_redirects",
                        return_value=_Response(json.dumps(payload).encode("utf-8")),
                    ),
                ):
                    with self.assertRaises(ExactInvocationError):
                        invoker.invoke_exact(
                            stage_authorization=authorization,
                            binding=binding,
                            prompt="Exact human prompt.",
                            max_tokens=64,
                            timeout_seconds=7,
                        )

    def test_incomplete_exact_finish_reasons_fail_closed(self) -> None:
        for finish_reason in ("length", "content_filter", None):
            with self.subTest(finish_reason=finish_reason):
                invoker = ExactProviderInvoker(self.store)
                authorization, binding = self.make_main_authorization()
                payload = {
                    "choices": [
                        {
                            "message": {"content": "syntactically complete but untrusted"},
                            "finish_reason": finish_reason,
                        }
                    ]
                }
                with (
                    patch.dict(os.environ, {"AOIA_PROVIDER_CALLS_ENABLED": "1"}, clear=False),
                    patch(
                        "runtime.providers.openai_compatible._open_without_redirects",
                        return_value=_Response(json.dumps(payload).encode("utf-8")),
                    ) as network,
                ):
                    with self.assertRaisesRegex(ExactInvocationError, "did not complete"):
                        invoker.invoke_exact(
                            stage_authorization=authorization,
                            binding=binding,
                            prompt="Exact human prompt.",
                            max_tokens=64,
                            timeout_seconds=7,
                        )
                network.assert_called_once()

    def test_provider_echo_of_secret_is_redacted_from_exact_result(self) -> None:
        calls: list[dict] = []
        invoker = ExactProviderInvoker(
            self.store,
            gateway_call=self.consuming_gateway(
                calls,
                response_text=f"echo {self.secret}",
            ),
        )
        authorization, binding = self.make_main_authorization()
        result = invoker.invoke_exact(
            stage_authorization=authorization,
            binding=binding,
            prompt="Exact human prompt.",
            max_tokens=64,
            timeout_seconds=7,
        )
        self.assertNotIn(self.secret, result.response_text)
        self.assertIn("REDACTED", result.response_text)


if __name__ == "__main__":
    unittest.main()
