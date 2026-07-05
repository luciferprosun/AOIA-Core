from __future__ import annotations

import ast
import copy
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.providers.payloads import build_provider_envelope
from runtime.providers.provider_payload_governance import (
    PAYLOAD_EXPANSION_BLOCKED_AMBIGUOUS_EVIDENCE,
    PAYLOAD_EXPANSION_BLOCKED_AUTHORITY_CLAIM,
    PAYLOAD_EXPANSION_BLOCKED_ENV_OR_SECRET,
    PAYLOAD_EXPANSION_BLOCKED_GIT_ACTION,
    PAYLOAD_EXPANSION_BLOCKED_NETWORK_OR_BROWSER,
    PAYLOAD_EXPANSION_BLOCKED_PACKAGE_INSTALL,
    PAYLOAD_EXPANSION_BLOCKED_RETRY_FALLBACK,
    PAYLOAD_EXPANSION_BLOCKED_SCHEMA_MISMATCH,
    PAYLOAD_EXPANSION_BLOCKED_STALE_EVIDENCE,
    PAYLOAD_EXPANSION_BLOCKED_STREAMING,
    PAYLOAD_EXPANSION_BLOCKED_TOOL_CALLING,
    PAYLOAD_EXPANSION_BLOCKED_UNBOUNDED_CONTEXT,
    PAYLOAD_EXPANSION_GOVERNANCE_ALLOWED_METADATA_ONLY,
    PAYLOAD_EXPANSION_GOVERNANCE_BLOCKED,
    PAYLOAD_EXPANSION_GOVERNANCE_REVIEW_REQUIRED,
    PAYLOAD_EXPANSION_OK_INERT_METADATA,
    PAYLOAD_EXPANSION_REQUIRES_HUMAN_REVIEW,
    PROVIDER_PAYLOAD_GOVERNANCE_SCHEMA_VERSION,
    compute_provider_payload_expansion_hash,
    evaluate_provider_payload_expansion_governance,
)


RUNTIME_FILE = Path(__file__).resolve().parents[1] / "runtime" / "providers" / "provider_payload_governance.py"
BASE_PAYLOAD_HASH = "d" * 64


class ProviderPayloadExpansionGovernance1ATests(unittest.TestCase):
    def test_inert_metadata_addition_is_metadata_only_and_deterministic(self):
        proposal = self.proposal(proposed_fields={"metadata": {"review_label": "step-40"}})

        first = evaluate_provider_payload_expansion_governance(
            proposal,
            current_tick=15,
            expected_provider_id="mock_chat",
            expected_base_payload_hash=BASE_PAYLOAD_HASH,
        )
        second = evaluate_provider_payload_expansion_governance(
            proposal,
            current_tick=15,
            expected_provider_id="mock_chat",
            expected_base_payload_hash=BASE_PAYLOAD_HASH,
        )

        self.assertEqual(first, second)
        self.assertEqual(PAYLOAD_EXPANSION_GOVERNANCE_ALLOWED_METADATA_ONLY, first.status)
        self.assertEqual((PAYLOAD_EXPANSION_OK_INERT_METADATA,), first.categories)
        self.assertEqual(("metadata",), first.proposed_field_names)
        self.assert_metadata_only(first.to_dict())

    def test_risky_fields_require_later_human_review_but_do_not_apply(self):
        proposal = self.proposal(proposed_fields={"response_format": {"type": "json_object"}})

        result = evaluate_provider_payload_expansion_governance(proposal, current_tick=15)

        self.assertEqual(PAYLOAD_EXPANSION_GOVERNANCE_REVIEW_REQUIRED, result.status)
        self.assertIn(PAYLOAD_EXPANSION_REQUIRES_HUMAN_REVIEW, result.categories)
        self.assert_metadata_only(result.to_dict())

    def test_forbidden_expansion_categories_fail_closed(self):
        cases = (
            ({"tools": [{"name": "write_file"}]}, PAYLOAD_EXPANSION_BLOCKED_TOOL_CALLING),
            ({"stream": True}, PAYLOAD_EXPANSION_BLOCKED_STREAMING),
            ({"fallback_provider": "other"}, PAYLOAD_EXPANSION_BLOCKED_RETRY_FALLBACK),
            ({"callback_url": "https://example.invalid/hook"}, PAYLOAD_EXPANSION_BLOCKED_NETWORK_OR_BROWSER),
            ({"package_install": "pip install unsafe"}, PAYLOAD_EXPANSION_BLOCKED_PACKAGE_INSTALL),
            ({"git_operation": "git push origin main"}, PAYLOAD_EXPANSION_BLOCKED_GIT_ACTION),
            ({"headers": {"Authorization": "Bearer token"}}, PAYLOAD_EXPANSION_BLOCKED_ENV_OR_SECRET),
            ({"metadata": {"can_execute": True}}, PAYLOAD_EXPANSION_BLOCKED_AUTHORITY_CLAIM),
            ({"full_context": "include whole repo"}, PAYLOAD_EXPANSION_BLOCKED_UNBOUNDED_CONTEXT),
        )

        for proposed_fields, category in cases:
            with self.subTest(category=category):
                result = evaluate_provider_payload_expansion_governance(
                    self.proposal(proposed_fields=proposed_fields),
                    current_tick=15,
                )

                self.assertEqual(PAYLOAD_EXPANSION_GOVERNANCE_BLOCKED, result.status)
                self.assertIn(category, result.categories)
                self.assert_metadata_only(result.to_dict())

    def test_unsupported_1a_fields_are_ambiguous_evidence(self):
        result = evaluate_provider_payload_expansion_governance(
            self.proposal(proposed_fields={"images": ["future-image-input"]}),
            current_tick=15,
        )

        self.assertEqual(PAYLOAD_EXPANSION_GOVERNANCE_BLOCKED, result.status)
        self.assertIn(PAYLOAD_EXPANSION_BLOCKED_AMBIGUOUS_EVIDENCE, result.categories)

    def test_malformed_unknown_or_excessive_evidence_fails_closed(self):
        cases = (
            "not a proposal",
            {},
            {**self.proposal(), "schema_version": "2A"},
            {**self.proposal(), "unexpected": "field"},
            {**self.proposal(), "proposed_fields": {}},
            {**self.proposal(), "proposed_fields": {f"field_{index}": index for index in range(9)}},
            {**self.proposal(), "proposed_fields": {"metadata": {"text": "x" * 2049}}},
        )

        for proposal in cases:
            with self.subTest(proposal=type(proposal).__name__):
                result = evaluate_provider_payload_expansion_governance(proposal, current_tick=15)

                self.assertEqual(PAYLOAD_EXPANSION_GOVERNANCE_BLOCKED, result.status)
                self.assertTrue(
                    {
                        PAYLOAD_EXPANSION_BLOCKED_SCHEMA_MISMATCH,
                        PAYLOAD_EXPANSION_BLOCKED_AMBIGUOUS_EVIDENCE,
                    }
                    & set(result.categories)
                )

    def test_expected_provider_base_hash_and_proposal_hash_mismatch_fail_closed(self):
        provider_mismatch = evaluate_provider_payload_expansion_governance(
            self.proposal(),
            current_tick=15,
            expected_provider_id="gemini_chat",
        )
        base_hash_mismatch = evaluate_provider_payload_expansion_governance(
            self.proposal(),
            current_tick=15,
            expected_base_payload_hash="e" * 64,
        )
        tampered = self.proposal()
        tampered["proposal_hash"] = "f" * 64
        proposal_hash_mismatch = evaluate_provider_payload_expansion_governance(
            tampered,
            current_tick=15,
        )

        for result in (provider_mismatch, base_hash_mismatch, proposal_hash_mismatch):
            self.assertEqual(PAYLOAD_EXPANSION_GOVERNANCE_BLOCKED, result.status)
            self.assertIn(PAYLOAD_EXPANSION_BLOCKED_SCHEMA_MISMATCH, result.categories)

    def test_stale_future_or_inverted_tick_evidence_fails_closed(self):
        cases = (
            self.proposal(created_at_tick=16, expires_at_tick=20),
            self.proposal(created_at_tick=10, expires_at_tick=14),
            self.proposal(created_at_tick=20, expires_at_tick=10),
        )

        for proposal in cases:
            with self.subTest(proposal=proposal):
                result = evaluate_provider_payload_expansion_governance(proposal, current_tick=15)

                self.assertEqual(PAYLOAD_EXPANSION_GOVERNANCE_BLOCKED, result.status)
                self.assertIn(PAYLOAD_EXPANSION_BLOCKED_STALE_EVIDENCE, result.categories)

    def test_result_authority_fields_are_forced_false(self):
        result = evaluate_provider_payload_expansion_governance(self.proposal(), current_tick=15)
        forced = replace(
            result,
            human_review_required=False,
            can_approve=True,
            can_execute=True,
            can_write=True,
            can_push=True,
            can_call_provider=True,
            can_change_gate=True,
            gate_satisfied=True,
            payload_expansion_applied=True,
        )

        self.assert_metadata_only(forced.to_dict())

    def test_governance_hash_changes_with_evidence_or_expectations(self):
        first = evaluate_provider_payload_expansion_governance(self.proposal(), current_tick=15)
        second = evaluate_provider_payload_expansion_governance(
            self.proposal(proposed_fields={"metadata": {"review_label": "changed"}}),
            current_tick=15,
        )
        third = evaluate_provider_payload_expansion_governance(
            self.proposal(),
            current_tick=15,
            expected_provider_id="mock_chat",
        )

        self.assertNotEqual(first.governance_hash, second.governance_hash)
        self.assertNotEqual(first.governance_hash, third.governance_hash)

    def test_does_not_mutate_proposal_or_live_provider_payload(self):
        proposal = self.proposal(proposed_fields={"response_format": {"type": "json_object"}})
        before_proposal = copy.deepcopy(proposal)
        envelope = build_provider_envelope(
            provider_id="mock_chat",
            model_id="mock-model",
            prompt="local prompt",
            params={"max_tokens": 32},
            created_at="2026-07-05T12:00:00Z",
        )
        before_envelope = envelope.to_dict()

        result = evaluate_provider_payload_expansion_governance(proposal, current_tick=15)

        self.assertEqual(before_proposal, proposal)
        self.assertEqual(before_envelope, envelope.to_dict())
        self.assertEqual(PAYLOAD_EXPANSION_GOVERNANCE_REVIEW_REQUIRED, result.status)
        self.assertFalse(result.payload_expansion_applied)

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
            "authorize",
        )

        for forbidden in forbidden_imports:
            self.assertNotIn(forbidden, scan.imports)
        for forbidden in forbidden_calls:
            self.assertNotIn(forbidden, scan.calls)
        for forbidden_text in ("shell=true", "os.environ", "getenv", "api_key"):
            self.assertNotIn(forbidden_text, source)

    @staticmethod
    def proposal(
        *,
        proposal_id: str = "payload-expansion-001",
        provider_id: str = "mock_chat",
        base_payload_hash: str = BASE_PAYLOAD_HASH,
        proposed_fields: dict | None = None,
        rationale: str = "Review inert payload metadata addition.",
        created_at_tick: int = 10,
        expires_at_tick: int = 20,
    ) -> dict:
        fields = {"metadata": {"review_label": "step-40"}} if proposed_fields is None else proposed_fields
        payload = {
            "schema_version": PROVIDER_PAYLOAD_GOVERNANCE_SCHEMA_VERSION,
            "proposal_id": proposal_id,
            "provider_id": provider_id,
            "base_payload_hash": base_payload_hash,
            "proposed_fields": fields,
            "rationale": rationale,
            "created_at_tick": created_at_tick,
            "expires_at_tick": expires_at_tick,
        }
        payload["proposal_hash"] = compute_provider_payload_expansion_hash(
            proposal_id=proposal_id,
            provider_id=provider_id,
            base_payload_hash=base_payload_hash,
            proposed_fields=fields,
            rationale=rationale,
            created_at_tick=created_at_tick,
            expires_at_tick=expires_at_tick,
        )
        return payload

    def assert_metadata_only(self, data: dict) -> None:
        self.assertTrue(data["human_review_required"])
        for field_name in (
            "can_approve",
            "can_execute",
            "can_write",
            "can_push",
            "can_call_provider",
            "can_change_gate",
            "gate_satisfied",
            "payload_expansion_applied",
        ):
            self.assertFalse(data[field_name])


def scan_module(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    calls: set[str] = set()
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
                aliases[alias.asname or alias.name.split(".", 1)[0]] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
            for alias in node.names:
                full_name = f"{node.module}.{alias.name}"
                imports.add(full_name)
                aliases[alias.asname or alias.name] = full_name
        elif isinstance(node, ast.Call):
            name = call_name(node.func, aliases)
            if name:
                calls.add(name)
    return type("Scan", (), {"imports": imports, "calls": calls})


def call_name(node: ast.AST, aliases: dict[str, str]) -> str:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        parts = attribute_parts(node)
        if not parts:
            return ""
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
