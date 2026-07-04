from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.providers.provider_gateway_guard import (
    PROVIDER_GATEWAY_GUARD_ALLOWED_METADATA_ONLY,
    PROVIDER_GATEWAY_GUARD_ALLOWED_REVIEW_ONLY,
    PROVIDER_GATEWAY_GUARD_BLOCKED,
    PROVIDER_GATEWAY_GUARD_BLOCKED_CIRCUIT_OPEN,
    PROVIDER_GATEWAY_GUARD_BLOCKED_FAILURE_THRESHOLD,
    PROVIDER_GATEWAY_GUARD_BLOCKED_IDENTITY_MISMATCH,
    PROVIDER_GATEWAY_GUARD_BLOCKED_MALFORMED_EVIDENCE,
    PROVIDER_GATEWAY_GUARD_BLOCKED_RATE_LIMIT,
    PROVIDER_GATEWAY_GUARD_BLOCKED_STALE_EVIDENCE,
    PROVIDER_GATEWAY_GUARD_SCHEMA_VERSION,
    ProviderGatewayGuardConfig,
    ProviderGatewayGuardState,
    compute_provider_gateway_guard_hash,
    create_provider_gateway_guard_state,
    default_provider_gateway_guard_config,
    evaluate_provider_gateway_guard,
)


RUNTIME_FILE = Path(__file__).resolve().parents[1] / "runtime" / "providers" / "provider_gateway_guard.py"
AUTHORITY_FIELDS = (
    "can_approve",
    "can_execute",
    "can_write",
    "can_push",
    "can_call_provider",
    "can_change_gate",
    "gate_satisfied",
)


class ProviderGatewayCircuitRateGuard1ATests(unittest.TestCase):
    def test_clean_preflight_pass_is_metadata_only_not_permission(self):
        result = evaluate_provider_gateway_guard(
            config=self.config(),
            state=self.state(),
            provider_id="mock_chat",
            operation_purpose="proposal_review",
            current_tick=100,
        )

        self.assertEqual(PROVIDER_GATEWAY_GUARD_ALLOWED_METADATA_ONLY, result.status)
        self.assertEqual((PROVIDER_GATEWAY_GUARD_ALLOWED_REVIEW_ONLY,), result.reason_codes)
        self.assertEqual(0, result.attempts_in_window)
        self.assert_metadata_only(result.to_dict())

    def test_circuit_open_blocks_until_caller_supplied_cooldown_tick(self):
        state = self.state(consecutive_failures=2, circuit_opened_at_tick=100)

        blocked = evaluate_provider_gateway_guard(
            config=self.config(failure_threshold=2, cooldown_seconds=50),
            state=state,
            provider_id="mock_chat",
            operation_purpose="proposal_review",
            current_tick=149,
        )
        reopened_metadata = evaluate_provider_gateway_guard(
            config=self.config(failure_threshold=2, cooldown_seconds=50),
            state=state,
            provider_id="mock_chat",
            operation_purpose="proposal_review",
            current_tick=150,
        )

        self.assertEqual(PROVIDER_GATEWAY_GUARD_BLOCKED, blocked.status)
        self.assertIn(PROVIDER_GATEWAY_GUARD_BLOCKED_CIRCUIT_OPEN, blocked.reason_codes)
        self.assertEqual(150, blocked.next_allowed_tick)
        self.assertEqual(PROVIDER_GATEWAY_GUARD_ALLOWED_METADATA_ONLY, reopened_metadata.status)
        self.assert_metadata_only(reopened_metadata.to_dict())

    def test_failure_threshold_blocks_when_circuit_evidence_was_not_opened(self):
        result = evaluate_provider_gateway_guard(
            config=self.config(failure_threshold=2),
            state=self.state(consecutive_failures=2),
            provider_id="mock_chat",
            operation_purpose="proposal_review",
            current_tick=100,
        )

        self.assertEqual(PROVIDER_GATEWAY_GUARD_BLOCKED, result.status)
        self.assertIn(PROVIDER_GATEWAY_GUARD_BLOCKED_FAILURE_THRESHOLD, result.reason_codes)
        self.assert_metadata_only(result.to_dict())

    def test_rate_window_limit_blocks_using_caller_supplied_tick(self):
        result = evaluate_provider_gateway_guard(
            config=self.config(max_attempts_per_window=2, window_seconds=10),
            state=self.state(recent_attempt_ticks=(91, 95, 100)),
            provider_id="mock_chat",
            operation_purpose="proposal_review",
            current_tick=100,
        )

        self.assertEqual(PROVIDER_GATEWAY_GUARD_BLOCKED, result.status)
        self.assertIn(PROVIDER_GATEWAY_GUARD_BLOCKED_RATE_LIMIT, result.reason_codes)
        self.assertEqual(3, result.attempts_in_window)

    def test_old_attempts_outside_rate_window_do_not_block(self):
        result = evaluate_provider_gateway_guard(
            config=self.config(max_attempts_per_window=2, window_seconds=10),
            state=self.state(recent_attempt_ticks=(1, 80)),
            provider_id="mock_chat",
            operation_purpose="proposal_review",
            current_tick=100,
        )

        self.assertEqual(PROVIDER_GATEWAY_GUARD_ALLOWED_METADATA_ONLY, result.status)
        self.assertEqual(0, result.attempts_in_window)

    def test_provider_identity_and_operation_purpose_mismatch_fail_closed(self):
        cases = (
            {"provider_id": "gemini_chat", "operation_purpose": "proposal_review"},
            {"provider_id": "mock_chat", "operation_purpose": "different_operation"},
        )

        for case in cases:
            with self.subTest(case=case):
                result = evaluate_provider_gateway_guard(
                    config=self.config(),
                    state=self.state(),
                    current_tick=100,
                    **case,
                )

                self.assertEqual(PROVIDER_GATEWAY_GUARD_BLOCKED, result.status)
                self.assertIn(PROVIDER_GATEWAY_GUARD_BLOCKED_IDENTITY_MISMATCH, result.reason_codes)

    def test_malformed_missing_or_invalid_evidence_fails_closed(self):
        cases = (
            {"config": {}, "state": self.state()},
            {"config": self.config(), "state": {}},
            {"config": self.config(max_attempts_per_window=1).to_dict(), "state": self.tampered_state_hash()},
            {"config": self.config().to_dict(), "state": self.state().to_dict(), "current_tick": -1},
        )

        for case in cases:
            with self.subTest(case=case.keys()):
                result = evaluate_provider_gateway_guard(
                    config=case.get("config", self.config()),
                    state=case.get("state", self.state()),
                    provider_id="mock_chat",
                    operation_purpose="proposal_review",
                    current_tick=case.get("current_tick", 100),
                )

                self.assertEqual(PROVIDER_GATEWAY_GUARD_BLOCKED, result.status)
                self.assertIn(PROVIDER_GATEWAY_GUARD_BLOCKED_MALFORMED_EVIDENCE, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_future_attempt_or_future_circuit_tick_is_stale_evidence(self):
        cases = (
            self.state(recent_attempt_ticks=(101,)),
            self.state(consecutive_failures=2, circuit_opened_at_tick=101),
        )

        for state in cases:
            with self.subTest(state=state.to_dict()):
                result = evaluate_provider_gateway_guard(
                    config=self.config(failure_threshold=2),
                    state=state,
                    provider_id="mock_chat",
                    operation_purpose="proposal_review",
                    current_tick=100,
                )

                self.assertEqual(PROVIDER_GATEWAY_GUARD_BLOCKED, result.status)
                self.assertIn(PROVIDER_GATEWAY_GUARD_BLOCKED_STALE_EVIDENCE, result.reason_codes)

    def test_guard_hash_is_deterministic_and_bound_to_evidence(self):
        left = evaluate_provider_gateway_guard(
            config=self.config(),
            state=self.state(),
            provider_id="mock_chat",
            operation_purpose="proposal_review",
            current_tick=100,
        )
        right = evaluate_provider_gateway_guard(
            config=self.config(),
            state=self.state(),
            provider_id="mock_chat",
            operation_purpose="proposal_review",
            current_tick=100,
        )
        changed_tick = evaluate_provider_gateway_guard(
            config=self.config(),
            state=self.state(),
            provider_id="mock_chat",
            operation_purpose="proposal_review",
            current_tick=101,
        )

        self.assertEqual(left.guard_hash, right.guard_hash)
        self.assertNotEqual(left.guard_hash, changed_tick.guard_hash)

    def test_state_hash_rejects_tampered_state_material(self):
        state = self.state()
        material = state.to_dict()
        material["recent_attempt_ticks"] = (99,)

        self.assertNotEqual(state.state_hash, compute_provider_gateway_guard_hash({key: value for key, value in material.items() if key != "state_hash"}))
        with self.assertRaises(ValueError):
            ProviderGatewayGuardState(**material)

    def test_metadata_cannot_override_blocked_result(self):
        blocked = evaluate_provider_gateway_guard(
            config=self.config(max_attempts_per_window=1),
            state=self.state(recent_attempt_ticks=(100,)),
            provider_id="mock_chat",
            operation_purpose="proposal_review",
            current_tick=100,
        )
        forced = replace(
            blocked,
            human_review_required=False,
            can_approve=True,
            can_execute=True,
            can_write=True,
            can_push=True,
            can_call_provider=True,
            can_change_gate=True,
            gate_satisfied=True,
        )

        self.assertEqual(PROVIDER_GATEWAY_GUARD_BLOCKED, forced.status)
        self.assert_metadata_only(forced.to_dict())

    def test_default_config_is_block_first_and_deterministic(self):
        first = default_provider_gateway_guard_config()
        second = default_provider_gateway_guard_config()

        self.assertEqual(first, second)
        self.assertEqual(1, first.max_attempts_per_window)
        self.assertEqual(PROVIDER_GATEWAY_GUARD_SCHEMA_VERSION, first.schema_version)

    def test_module_has_no_provider_network_browser_package_env_or_runtime_call_surface(self):
        source = RUNTIME_FILE.read_text(encoding="utf-8").casefold()
        scan = scan_module(RUNTIME_FILE)

        forbidden_imports = (
            "os",
            "subprocess",
            "socket",
            "urllib",
            "requests",
            "httpx",
            "aiohttp",
            "webbrowser",
            "selenium",
            "playwright",
            "openai",
            "anthropic",
            "runtime.providers.gateway",
            "runtime.provider_live_adapter",
            "runtime.execution",
            "runtime.control_write",
        )
        forbidden_calls = (
            "open",
            "print",
            "eval",
            "exec",
            "subprocess.run",
            "os.system",
            "write",
            "write_text",
            "write_bytes",
            "dispatch",
            "execute",
            "approve",
            "authorize",
        )

        for forbidden in forbidden_imports:
            self.assertNotIn(forbidden, scan.imports)
        for forbidden in forbidden_calls:
            self.assertNotIn(forbidden, scan.calls)
        for forbidden_text in ("shell=true", "os.environ", "getenv", "api_key"):
            self.assertNotIn(forbidden_text, source)

    @staticmethod
    def config(**overrides) -> ProviderGatewayGuardConfig:
        payload = {
            "schema_version": PROVIDER_GATEWAY_GUARD_SCHEMA_VERSION,
            "max_attempts_per_window": 3,
            "window_seconds": 60,
            "failure_threshold": 3,
            "cooldown_seconds": 300,
        }
        payload.update(overrides)
        return ProviderGatewayGuardConfig(**payload)

    @staticmethod
    def state(**overrides) -> ProviderGatewayGuardState:
        payload = {
            "provider_id": "mock_chat",
            "operation_purpose": "proposal_review",
            "consecutive_failures": 0,
            "circuit_opened_at_tick": None,
            "recent_attempt_ticks": (),
        }
        payload.update(overrides)
        return create_provider_gateway_guard_state(**payload)

    @staticmethod
    def tampered_state_hash() -> dict:
        payload = create_provider_gateway_guard_state(
            provider_id="mock_chat",
            operation_purpose="proposal_review",
        ).to_dict()
        payload["state_hash"] = "0" * 64
        return payload

    def assert_metadata_only(self, data: dict) -> None:
        self.assertTrue(data["human_review_required"])
        for field in AUTHORITY_FIELDS:
            self.assertFalse(data.get(field, False))


def scan_module(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    calls: list[str] = []
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
                aliases[alias.asname or alias.name.split(".", 1)[0]] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
            for alias in node.names:
                aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
        elif isinstance(node, ast.Call):
            name = call_name(node.func, aliases)
            if name:
                calls.append(name)
    return type("Scan", (), {"imports": tuple(imports), "calls": tuple(calls)})()


def call_name(node: ast.AST, aliases: dict[str, str]) -> str:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        parts = attribute_parts(node)
        if parts:
            return ".".join((aliases.get(parts[0], parts[0]), *parts[1:]))
    return ""


def attribute_parts(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, ast.Attribute):
        return (*attribute_parts(node.value), node.attr)
    return ()


if __name__ == "__main__":
    unittest.main()
