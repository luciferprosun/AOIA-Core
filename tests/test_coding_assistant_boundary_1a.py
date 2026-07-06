from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.integration_boundaries.coding_assistant_boundary import (
    CODING_ASSISTANT_BOUNDARY_BLOCKED,
    CODING_ASSISTANT_BOUNDARY_BLOCKED_AUTHORITY_CLAIM,
    CODING_ASSISTANT_BOUNDARY_BLOCKED_AUTONOMOUS_EVIDENCE,
    CODING_ASSISTANT_BOUNDARY_BLOCKED_EFFECT_EVIDENCE,
    CODING_ASSISTANT_BOUNDARY_BLOCKED_EXECUTABLE_EVIDENCE,
    CODING_ASSISTANT_BOUNDARY_BLOCKED_HASH_MISMATCH,
    CODING_ASSISTANT_BOUNDARY_BLOCKED_MALFORMED_EVIDENCE,
    CODING_ASSISTANT_BOUNDARY_BLOCKED_NON_JSON_SERIALIZABLE,
    CODING_ASSISTANT_BOUNDARY_BLOCKED_POLICY_CAPABILITY,
    CODING_ASSISTANT_BOUNDARY_BLOCKED_STALE_EVIDENCE,
    CODING_ASSISTANT_BOUNDARY_BLOCKED_UNKNOWN_FIELD,
    CODING_ASSISTANT_BOUNDARY_READY_METADATA_ONLY,
    CODING_ASSISTANT_BOUNDARY_REASON_READY_METADATA_ONLY,
    CODING_ASSISTANT_BOUNDARY_RISK_BLOCKED,
    CODING_ASSISTANT_BOUNDARY_RISK_MEDIUM,
    CodingAssistantBoundaryReviewResult,
    canonical_coding_assistant_boundary_json,
    create_coding_assistant_capability_declaration,
    create_coding_assistant_output_envelope,
    create_coding_assistant_request_envelope,
    review_coding_assistant_boundary,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "integration_boundaries" / "coding_assistant_boundary.py"


class CodingAssistantBoundary1ATests(unittest.TestCase):
    def test_valid_codex_style_metadata_review_is_inert_hash_bound_and_not_authority(self):
        evidence = self.evidence()

        result = review_coding_assistant_boundary(**evidence, now_tick=12)

        self.assertEqual(CODING_ASSISTANT_BOUNDARY_READY_METADATA_ONLY, result.status)
        self.assertEqual((CODING_ASSISTANT_BOUNDARY_REASON_READY_METADATA_ONLY,), result.reason_codes)
        self.assertEqual(CODING_ASSISTANT_BOUNDARY_RISK_MEDIUM, result.risk_tier)
        self.assertEqual(evidence["capability_declaration"].declaration_hash, result.declaration_hash)
        self.assertEqual(evidence["request_envelope"].request_hash, result.request_hash)
        self.assertEqual(evidence["output_envelope"].output_hash, result.output_hash)
        self.assertIn("explicit_hash_bound_human_approval", result.required_future_evidence)
        self.assertIn("separate_controlled_patch_or_execution_path", result.required_future_evidence)
        self.assert_metadata_only(result.to_dict())

    def test_hashes_and_canonical_json_are_deterministic(self):
        first = review_coding_assistant_boundary(**self.evidence(), now_tick=12)
        second = review_coding_assistant_boundary(**self.evidence(), now_tick=12)

        self.assertEqual(first.review_hash, second.review_hash)
        self.assertEqual(
            canonical_coding_assistant_boundary_json({"b": 1, "a": ("x",)}),
            canonical_coding_assistant_boundary_json({"a": ["x"], "b": 1}),
        )

    def test_forbidden_capabilities_fail_closed_as_metadata(self):
        evidence = self.evidence(requested_capabilities=("invoke_codex", "apply_patch", "git_operation"))

        result = review_coding_assistant_boundary(**evidence, now_tick=12)

        self.assertEqual(CODING_ASSISTANT_BOUNDARY_BLOCKED, result.status)
        self.assertIn(CODING_ASSISTANT_BOUNDARY_BLOCKED_POLICY_CAPABILITY, result.reason_codes)
        self.assertEqual(CODING_ASSISTANT_BOUNDARY_RISK_BLOCKED, result.risk_tier)
        self.assertEqual(("apply_patch", "git_operation", "invoke_codex"), result.blocked_capabilities)
        self.assert_metadata_only(result.to_dict())

    def test_missing_stale_unknown_non_json_and_hash_tampering_fail_closed(self):
        evidence = self.evidence()
        bad_request = evidence["request_envelope"].to_dict()
        bad_request["request_hash"] = "0" * 64
        cases = (
            ({**evidence, "capability_declaration": {}}, CODING_ASSISTANT_BOUNDARY_BLOCKED_MALFORMED_EVIDENCE),
            ({**evidence, "request_envelope": {**evidence["request_envelope"].to_dict(), "unknown": "field"}}, CODING_ASSISTANT_BOUNDARY_BLOCKED_UNKNOWN_FIELD),
            ({**evidence, "output_envelope": {**evidence["output_envelope"].to_dict(), "metadata": {"bad": object()}}}, CODING_ASSISTANT_BOUNDARY_BLOCKED_NON_JSON_SERIALIZABLE),
            ({**evidence, "request_envelope": bad_request}, CODING_ASSISTANT_BOUNDARY_BLOCKED_HASH_MISMATCH),
            (
                {
                    **evidence,
                    "request_envelope": self.request(
                        evidence["capability_declaration"],
                        created_at_tick=1,
                        expires_at_tick=5,
                    ),
                },
                CODING_ASSISTANT_BOUNDARY_BLOCKED_HASH_MISMATCH,
            ),
        )
        for altered, reason in cases:
            with self.subTest(reason=reason):
                result = review_coding_assistant_boundary(**altered, now_tick=12)

                self.assertEqual(CODING_ASSISTANT_BOUNDARY_BLOCKED, result.status)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_stale_output_fails_closed(self):
        evidence = self.evidence()
        expired_output = create_coding_assistant_output_envelope(
            output_id="assistant-output",
            assistant_kind="codex",
            request_hash=evidence["request_envelope"].request_hash,
            capability_declaration_hash=evidence["capability_declaration"].declaration_hash,
            output_kind="review_notes",
            output_text="Review metadata only.",
            generated_at_tick=1,
            expires_at_tick=5,
            metadata={"source": "unit-test"},
        )

        result = review_coding_assistant_boundary(
            capability_declaration=evidence["capability_declaration"],
            request_envelope=evidence["request_envelope"],
            output_envelope=expired_output,
            now_tick=12,
        )

        self.assertEqual(CODING_ASSISTANT_BOUNDARY_BLOCKED, result.status)
        self.assertIn(CODING_ASSISTANT_BOUNDARY_BLOCKED_STALE_EVIDENCE, result.reason_codes)
        self.assert_metadata_only(result.to_dict())

    def test_authority_effect_executable_and_autonomous_claims_fail_closed(self):
        evidence = self.evidence()
        cases = (
            ({**evidence, "request_envelope": {**evidence["request_envelope"].to_dict(), "can_execute": True}}, CODING_ASSISTANT_BOUNDARY_BLOCKED_AUTHORITY_CLAIM),
            ({**evidence, "output_envelope": {**evidence["output_envelope"].to_dict(), "patch_applied": True}}, CODING_ASSISTANT_BOUNDARY_BLOCKED_EFFECT_EVIDENCE),
            ({**evidence, "output_envelope": {**evidence["output_envelope"].to_dict(), "metadata": {"command": "git status"}}}, CODING_ASSISTANT_BOUNDARY_BLOCKED_EXECUTABLE_EVIDENCE),
            ({**evidence, "request_envelope": {**evidence["request_envelope"].to_dict(), "metadata": {"auto_apply": True}}}, CODING_ASSISTANT_BOUNDARY_BLOCKED_AUTONOMOUS_EVIDENCE),
        )
        for altered, reason in cases:
            with self.subTest(reason=reason):
                result = review_coding_assistant_boundary(**altered, now_tick=12)

                self.assertEqual(CODING_ASSISTANT_BOUNDARY_BLOCKED, result.status)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_result_cannot_satisfy_gate_or_grant_authority_even_if_replaced(self):
        result = review_coding_assistant_boundary(**self.evidence(), now_tick=12)
        forced = replace(
            result,
            codex_run=True,
            aider_run=True,
            coding_agent_cli_called=True,
            process_started=True,
            shell_called=True,
            git_action_performed=True,
            package_manager_called=True,
            browser_automation_started=True,
            provider_called=True,
            mcp_called=True,
            tool_call_invoked=True,
            patch_applied=True,
            repo_file_written=True,
            dispatcher_created=True,
            agent_loop_started=True,
            approval_created=True,
            gate_satisfied=True,
            human_barrier_satisfied=True,
            boundary_passed=True,
            can_apply=True,
            can_execute=True,
            can_commit=True,
            can_push=True,
            can_write=True,
            can_call_provider=True,
            can_change_gate=True,
            agent_allowed=True,
        )

        self.assert_metadata_only(forced.to_dict())
        for method_name in ("run", "execute", "dispatch", "apply", "apply_patch", "commit", "push"):
            self.assertFalse(hasattr(result, method_name))

    def test_boundary_result_rejects_invalid_status_and_risk(self):
        result = review_coding_assistant_boundary(**self.evidence(), now_tick=12)
        data = result.to_dict()

        with self.assertRaises(ValueError):
            CodingAssistantBoundaryReviewResult(**{**data, "status": "EXECUTE"})
        with self.assertRaises(ValueError):
            CodingAssistantBoundaryReviewResult(**{**data, "risk_tier": "APPROVED"})

    def test_module_static_surface_is_boundary_only(self):
        source = RUNTIME_FILE.read_text(encoding="utf-8").casefold()
        scan = scan_module(RUNTIME_FILE)

        for forbidden_import in (
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
            "runtime.control_write",
            "runtime.execution",
            "runtime.git_ops",
            "runtime.package_ops.controlled_package_install",
        ):
            self.assertNotIn(forbidden_import, scan.imports)
        for forbidden_call in (
            "subprocess.run",
            "subprocess.Popen",
            "os.system",
            "eval",
            "exec",
            "__import__",
            "importlib.import_module",
        ):
            self.assertNotIn(forbidden_call, scan.calls)
        for forbidden_text in ("shell=true", "os.environ", "getenv", "api_key", "step 49", "step 52", "step 53", "step 54"):
            self.assertNotIn(forbidden_text, source)

    def evidence(self, *, requested_capabilities=("read_context_metadata", "propose_patch_metadata", "summarize_findings")):
        declaration = create_coding_assistant_capability_declaration(
            assistant_kind="codex",
            requested_capabilities=requested_capabilities,
        )
        request = self.request(declaration)
        output = create_coding_assistant_output_envelope(
            output_id="assistant-output",
            assistant_kind="codex",
            request_hash=request.request_hash,
            capability_declaration_hash=declaration.declaration_hash,
            output_kind="review_notes",
            output_text="Review metadata only. Proposed change summary is inert.",
            generated_at_tick=10,
            expires_at_tick=20,
            metadata={"source": "unit-test"},
        )
        return {
            "capability_declaration": declaration,
            "request_envelope": request,
            "output_envelope": output,
        }

    def request(self, declaration, *, created_at_tick=10, expires_at_tick=20):
        return create_coding_assistant_request_envelope(
            request_id="assistant-request",
            assistant_kind="codex",
            objective="Review a proposed change as metadata only.",
            target_refs=("runtime/example.py",),
            context_hashes=("1" * 64,),
            capability_declaration_hash=declaration.declaration_hash,
            requested_by="tester",
            created_at_tick=created_at_tick,
            expires_at_tick=expires_at_tick,
            metadata={"source": "unit-test"},
        )

    def assert_metadata_only(self, data):
        for field in (
            "codex_run",
            "aider_run",
            "coding_agent_cli_called",
            "process_started",
            "shell_called",
            "git_action_performed",
            "package_manager_called",
            "browser_automation_started",
            "provider_called",
            "mcp_called",
            "tool_call_invoked",
            "patch_applied",
            "repo_file_written",
            "dispatcher_created",
            "agent_loop_started",
            "approval_created",
            "gate_satisfied",
            "human_barrier_satisfied",
            "boundary_passed",
            "can_apply",
            "can_execute",
            "can_commit",
            "can_push",
            "can_write",
            "can_call_provider",
            "can_change_gate",
            "agent_allowed",
        ):
            self.assertIs(data[field], False)
        self.assertIs(data["human_review_required"], True)


def scan_module(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
        elif isinstance(node, ast.Call):
            calls.add(call_name(node.func))
    return type("Scan", (), {"imports": tuple(sorted(imports)), "calls": tuple(sorted(calls))})()


def call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = call_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


if __name__ == "__main__":
    unittest.main()
