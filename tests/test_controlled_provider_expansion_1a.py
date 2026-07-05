from __future__ import annotations

import ast
import copy
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.providers.provider_controlled_expansion import (
    CONTROLLED_PROVIDER_EXPANSION_APPLIED_INERT,
    CONTROLLED_PROVIDER_EXPANSION_BLOCKED,
    CONTROLLED_PROVIDER_EXPANSION_BLOCKED_AUTHORITY_CLAIM,
    CONTROLLED_PROVIDER_EXPANSION_BLOCKED_BARRIER_HASH_MISMATCH,
    CONTROLLED_PROVIDER_EXPANSION_BLOCKED_BARRIER_SCOPE_MISMATCH,
    CONTROLLED_PROVIDER_EXPANSION_BLOCKED_DANGEROUS_FIELD,
    CONTROLLED_PROVIDER_EXPANSION_BLOCKED_FIELD_NOT_APPROVED,
    CONTROLLED_PROVIDER_EXPANSION_BLOCKED_GOVERNANCE_NOT_ALLOWED,
    CONTROLLED_PROVIDER_EXPANSION_BLOCKED_HASH_MISMATCH,
    CONTROLLED_PROVIDER_EXPANSION_BLOCKED_MALFORMED_EVIDENCE,
    CONTROLLED_PROVIDER_EXPANSION_BLOCKED_MISSING_HUMAN_BARRIER,
    CONTROLLED_PROVIDER_EXPANSION_BLOCKED_PAYLOAD_COLLISION,
    CONTROLLED_PROVIDER_EXPANSION_REASON_APPLIED_INERT,
    ProviderExpansionHumanBarrier,
    apply_controlled_provider_expansion,
    compute_provider_base_payload_hash,
    compute_provider_expansion_barrier_hash,
    create_provider_expansion_human_barrier,
)
from runtime.providers.provider_payload_governance import (
    PAYLOAD_EXPANSION_GOVERNANCE_BLOCKED,
    PAYLOAD_EXPANSION_GOVERNANCE_REVIEW_REQUIRED,
    PROVIDER_PAYLOAD_GOVERNANCE_SCHEMA_VERSION,
    compute_provider_payload_expansion_hash,
    evaluate_provider_payload_expansion_governance,
)


RUNTIME_FILE = Path(__file__).resolve().parents[1] / "runtime" / "providers" / "provider_controlled_expansion.py"


class ControlledProviderExpansion1ATests(unittest.TestCase):
    def test_valid_inert_metadata_expansion_returns_new_inert_payload(self):
        evidence = self.reviewed_evidence(proposed_fields={"metadata": {"review_label": "step-41"}})

        result = apply_controlled_provider_expansion(**evidence)

        self.assertEqual(CONTROLLED_PROVIDER_EXPANSION_APPLIED_INERT, result.status)
        self.assertEqual((CONTROLLED_PROVIDER_EXPANSION_REASON_APPLIED_INERT,), result.reason_codes)
        self.assertEqual(("metadata",), result.applied_fields)
        self.assertEqual("step-41", result.expanded_payload["metadata"]["review_label"])
        self.assertNotIn("metadata", evidence["base_payload"])
        self.assertEqual(compute_provider_base_payload_hash(result.expanded_payload), result.expanded_payload_hash)
        self.assert_metadata_only(result.to_dict(), expanded=True)

    def test_review_required_field_can_apply_only_with_explicit_hash_bound_barrier(self):
        evidence = self.reviewed_evidence(
            proposed_fields={"response_format": {"type": "json_object"}},
        )
        self.assertEqual(PAYLOAD_EXPANSION_GOVERNANCE_REVIEW_REQUIRED, evidence["governance_result"].status)

        result = apply_controlled_provider_expansion(**evidence)

        self.assertEqual(CONTROLLED_PROVIDER_EXPANSION_APPLIED_INERT, result.status)
        self.assertEqual({"type": "json_object"}, result.expanded_payload["response_format"])
        self.assert_metadata_only(result.to_dict(), expanded=True)

    def test_missing_or_malformed_inputs_fail_closed(self):
        evidence = self.reviewed_evidence()
        cases = (
            {**evidence, "base_payload": None},
            {**evidence, "proposal": None},
            {**evidence, "governance_result": None},
            {**evidence, "human_barrier": None},
        )

        for case in cases:
            with self.subTest(case=case.keys()):
                result = apply_controlled_provider_expansion(**case)

                self.assertEqual(CONTROLLED_PROVIDER_EXPANSION_BLOCKED, result.status)
                self.assertTrue(
                    {
                        CONTROLLED_PROVIDER_EXPANSION_BLOCKED_MALFORMED_EVIDENCE,
                        CONTROLLED_PROVIDER_EXPANSION_BLOCKED_MISSING_HUMAN_BARRIER,
                    }
                    & set(result.reason_codes)
                )
                self.assert_metadata_only(result.to_dict())

    def test_blocked_governance_never_applies_even_with_barrier(self):
        evidence = self.reviewed_evidence(proposed_fields={"tools": [{"name": "write_file"}]})
        self.assertEqual(PAYLOAD_EXPANSION_GOVERNANCE_BLOCKED, evidence["governance_result"].status)

        result = apply_controlled_provider_expansion(**evidence)

        self.assertEqual(CONTROLLED_PROVIDER_EXPANSION_BLOCKED, result.status)
        self.assertIn(CONTROLLED_PROVIDER_EXPANSION_BLOCKED_GOVERNANCE_NOT_ALLOWED, result.reason_codes)
        self.assertIn(CONTROLLED_PROVIDER_EXPANSION_BLOCKED_DANGEROUS_FIELD, result.reason_codes)
        self.assertIsNone(result.expanded_payload)

    def test_base_proposal_and_governance_hash_mismatches_fail_closed(self):
        evidence = self.reviewed_evidence()
        tampered_base = {**evidence["base_payload"], "extra": "changed"}
        tampered_proposal = {**evidence["proposal"], "proposal_hash": "0" * 64}
        tampered_governance = {
            **evidence["governance_result"].to_dict(),
            "governance_hash": "1" * 64,
        }

        for case in (
            {**evidence, "base_payload": tampered_base},
            {**evidence, "proposal": tampered_proposal},
            {**evidence, "governance_result": tampered_governance},
        ):
            with self.subTest(case=case):
                result = apply_controlled_provider_expansion(**case)

                self.assertEqual(CONTROLLED_PROVIDER_EXPANSION_BLOCKED, result.status)
                self.assertIn(CONTROLLED_PROVIDER_EXPANSION_BLOCKED_HASH_MISMATCH, result.reason_codes)

    def test_barrier_hash_scope_and_approved_fields_are_required(self):
        evidence = self.reviewed_evidence()
        wrong_hash = {**evidence["human_barrier"].to_dict(), "barrier_hash": "2" * 64}
        wrong_scope = self.barrier(evidence, provider_id="gemini_chat")
        wrong_fields = self.barrier(evidence, approved_fields=("review_note",))

        cases = (
            (wrong_hash, CONTROLLED_PROVIDER_EXPANSION_BLOCKED_BARRIER_HASH_MISMATCH),
            (wrong_scope, CONTROLLED_PROVIDER_EXPANSION_BLOCKED_BARRIER_SCOPE_MISMATCH),
            (wrong_fields, CONTROLLED_PROVIDER_EXPANSION_BLOCKED_FIELD_NOT_APPROVED),
        )
        for barrier, reason in cases:
            with self.subTest(reason=reason):
                result = apply_controlled_provider_expansion(
                    base_payload=evidence["base_payload"],
                    proposal=evidence["proposal"],
                    governance_result=evidence["governance_result"],
                    human_barrier=barrier,
                )

                self.assertEqual(CONTROLLED_PROVIDER_EXPANSION_BLOCKED, result.status)
                self.assertIn(reason, result.reason_codes)

    def test_human_barrier_authority_flags_cannot_enable_provider_call_or_gate(self):
        evidence = self.reviewed_evidence()
        forced = replace(
            evidence["human_barrier"],
            can_call_provider=True,
            can_execute=True,
            can_write=True,
            gate_satisfied=True,
            human_barrier_satisfied=True,
        )

        result = apply_controlled_provider_expansion(
            base_payload=evidence["base_payload"],
            proposal=evidence["proposal"],
            governance_result=evidence["governance_result"],
            human_barrier=forced,
        )

        self.assertEqual(CONTROLLED_PROVIDER_EXPANSION_APPLIED_INERT, result.status)
        self.assertFalse(forced.can_call_provider)
        self.assertFalse(forced.gate_satisfied)
        self.assert_metadata_only(result.to_dict(), expanded=True)

    def test_provider_claims_approved_or_safe_are_not_a_valid_barrier(self):
        evidence = self.reviewed_evidence()
        forged_barrier = {
            "approved": True,
            "safe": True,
            "can_call_provider": True,
            "authority": True,
        }

        result = apply_controlled_provider_expansion(
            base_payload=evidence["base_payload"],
            proposal=evidence["proposal"],
            governance_result=evidence["governance_result"],
            human_barrier=forged_barrier,
        )

        self.assertEqual(CONTROLLED_PROVIDER_EXPANSION_BLOCKED, result.status)
        self.assertIn(CONTROLLED_PROVIDER_EXPANSION_BLOCKED_MALFORMED_EVIDENCE, result.reason_codes)

    def test_dangerous_fields_always_fail_closed_even_if_governance_is_forged_allowed(self):
        evidence = self.reviewed_evidence(proposed_fields={"stream": True})
        forged_governance = evidence["governance_result"].to_dict()
        forged_governance["status"] = "PAYLOAD_EXPANSION_GOVERNANCE_ALLOWED_METADATA_ONLY"
        forged_governance["categories"] = ("PAYLOAD_EXPANSION_OK_INERT_METADATA",)
        forged_governance["proposed_field_names"] = ("stream",)
        forged_barrier = self.barrier(
            {
                **evidence,
                "governance_result": type("Gov", (), {"to_dict": lambda _self: forged_governance})(),
            },
            approved_fields=("stream",),
        )

        result = apply_controlled_provider_expansion(
            base_payload=evidence["base_payload"],
            proposal=evidence["proposal"],
            governance_result=forged_governance,
            human_barrier=forged_barrier,
        )

        self.assertEqual(CONTROLLED_PROVIDER_EXPANSION_BLOCKED, result.status)
        self.assertIn(CONTROLLED_PROVIDER_EXPANSION_BLOCKED_DANGEROUS_FIELD, result.reason_codes)

    def test_payload_field_collision_fails_closed_without_mutating_base(self):
        evidence = self.reviewed_evidence(proposed_fields={"model": "changed-model"})
        before = copy.deepcopy(evidence["base_payload"])
        forged_governance = evidence["governance_result"].to_dict()
        forged_governance["status"] = "PAYLOAD_EXPANSION_GOVERNANCE_REVIEW_REQUIRED"
        forged_governance["categories"] = ("PAYLOAD_EXPANSION_REQUIRES_HUMAN_REVIEW",)
        forged_governance["proposed_field_names"] = ("model",)
        forged_barrier = self.barrier(
            {
                **evidence,
                "governance_result": type("Gov", (), {"to_dict": lambda _self: forged_governance})(),
            },
            approved_fields=("model",),
        )

        result = apply_controlled_provider_expansion(
            base_payload=evidence["base_payload"],
            proposal=evidence["proposal"],
            governance_result=forged_governance,
            human_barrier=forged_barrier,
        )

        self.assertEqual(CONTROLLED_PROVIDER_EXPANSION_BLOCKED, result.status)
        self.assertIn(CONTROLLED_PROVIDER_EXPANSION_BLOCKED_PAYLOAD_COLLISION, result.reason_codes)
        self.assertEqual(before, evidence["base_payload"])

    def test_result_hash_is_deterministic_and_changes_with_expanded_payload(self):
        first = apply_controlled_provider_expansion(**self.reviewed_evidence())
        second = apply_controlled_provider_expansion(**self.reviewed_evidence())
        changed = apply_controlled_provider_expansion(
            **self.reviewed_evidence(proposed_fields={"metadata": {"review_label": "changed"}})
        )

        self.assertEqual(first.result_hash, second.result_hash)
        self.assertNotEqual(first.result_hash, changed.result_hash)

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

    def reviewed_evidence(self, *, proposed_fields: dict | None = None):
        base_payload = {
            "model": "mock-model",
            "messages": ({"role": "user", "content": "local inert prompt"},),
        }
        proposal = self.proposal(base_payload, proposed_fields=proposed_fields)
        governance = evaluate_provider_payload_expansion_governance(
            proposal,
            current_tick=15,
            expected_provider_id=proposal["provider_id"],
            expected_base_payload_hash=proposal["base_payload_hash"],
        )
        evidence = {
            "base_payload": base_payload,
            "proposal": proposal,
            "governance_result": governance,
        }
        evidence["human_barrier"] = self.barrier(evidence)
        return evidence

    def proposal(self, base_payload: dict, *, proposed_fields: dict | None = None) -> dict:
        fields = {"metadata": {"review_label": "step-41"}} if proposed_fields is None else proposed_fields
        payload = {
            "schema_version": PROVIDER_PAYLOAD_GOVERNANCE_SCHEMA_VERSION,
            "proposal_id": "payload-expansion-001",
            "provider_id": "mock_chat",
            "base_payload_hash": compute_provider_base_payload_hash(base_payload),
            "proposed_fields": fields,
            "rationale": "Review controlled inert provider payload expansion.",
            "created_at_tick": 10,
            "expires_at_tick": 20,
        }
        payload["proposal_hash"] = compute_provider_payload_expansion_hash(
            proposal_id=payload["proposal_id"],
            provider_id=payload["provider_id"],
            base_payload_hash=payload["base_payload_hash"],
            proposed_fields=fields,
            rationale=payload["rationale"],
            created_at_tick=payload["created_at_tick"],
            expires_at_tick=payload["expires_at_tick"],
        )
        return payload

    def barrier(self, evidence: dict, **overrides) -> ProviderExpansionHumanBarrier:
        governance = evidence["governance_result"].to_dict()
        values = {
            "proposal_hash": evidence["proposal"]["proposal_hash"],
            "governance_hash": governance["governance_hash"],
            "base_payload_hash": evidence["proposal"]["base_payload_hash"],
            "provider_id": evidence["proposal"]["provider_id"],
            "approved_fields": tuple(governance["proposed_field_names"]),
            "approved_by": "local-human-reviewer",
            "approval_reason": "Hash-bound approval for inert payload expansion only.",
        }
        values.update(overrides)
        return create_provider_expansion_human_barrier(**values)

    def assert_metadata_only(self, data: dict, *, expanded: bool = False) -> None:
        self.assertTrue(data["human_review_required"])
        self.assertEqual(expanded, data["inert_payload_expanded"])
        for field_name in (
            "provider_called",
            "network_called",
            "execution_performed",
            "file_written",
            "browser_opened",
            "package_installed",
            "git_action_performed",
            "can_approve",
            "can_execute",
            "can_write",
            "can_push",
            "can_call_provider",
            "can_change_gate",
            "gate_satisfied",
            "human_barrier_satisfied",
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
