from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.patches.controlled_patch_apply import (
    CONTROLLED_PATCH_APPLIED,
    CONTROLLED_PATCH_BLOCKED,
    CONTROLLED_PATCH_FILE_APPLIED,
    CONTROLLED_PATCH_PARTIAL,
    ControlledPatchApplyFileResult,
    ControlledPatchApplyResult,
    compute_controlled_patch_apply_hash,
)
from runtime.patches.patch_barrier import PATCH_DECISION_APPROVE, create_human_patch_barrier
from runtime.patches.patch_policy import PATCH_POLICY_NEEDS_REVIEW, check_patch_local_policy
from runtime.patches.patch_preview import PatchFileEdit, build_patch_preview
from runtime.patches.post_patch_verification_plan import (
    POST_PATCH_VERIFICATION_BLOCKED,
    POST_PATCH_VERIFICATION_BLOCKED_APPLY_FAILED,
    POST_PATCH_VERIFICATION_BLOCKED_APPLY_HASH_MISMATCH,
    POST_PATCH_VERIFICATION_BLOCKED_AUTHORITY_CLAIM,
    POST_PATCH_VERIFICATION_BLOCKED_BARRIER_HASH_MISMATCH,
    POST_PATCH_VERIFICATION_BLOCKED_CONTENT_HASH_MISMATCH,
    POST_PATCH_VERIFICATION_BLOCKED_MISSING_APPLY,
    POST_PATCH_VERIFICATION_BLOCKED_MISSING_BARRIER,
    POST_PATCH_VERIFICATION_BLOCKED_MISSING_POLICY,
    POST_PATCH_VERIFICATION_BLOCKED_MISSING_PREVIEW,
    POST_PATCH_VERIFICATION_BLOCKED_PARTIAL_APPLY,
    POST_PATCH_VERIFICATION_BLOCKED_POLICY_HASH_MISMATCH,
    POST_PATCH_VERIFICATION_BLOCKED_PREVIEW_HASH_MISMATCH,
    POST_PATCH_VERIFICATION_BLOCKED_TARGET_MISMATCH,
    POST_PATCH_VERIFICATION_READY,
    PostPatchVerificationPlanResult,
    build_post_patch_verification_plan,
    canonical_post_patch_verification_plan_json,
    compute_post_patch_verification_plan_hash,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_MODULE = REPO_ROOT / "runtime" / "patches" / "post_patch_verification_plan.py"


class PostPatchVerificationPlan1ATests(unittest.TestCase):
    def test_valid_controlled_patch_apply_produces_ready_verification_plan(self):
        evidence = self.evidence("runtime/patches/controlled_patch_apply.py")

        result = self.plan(evidence)

        self.assertEqual(POST_PATCH_VERIFICATION_READY, result.status)
        self.assertTrue(result.plan_ready)
        self.assertEqual(evidence["apply"].apply_hash, result.apply_hash)
        self.assertEqual(evidence["preview"].preview_hash, result.patch_preview_hash)
        self.assertEqual(evidence["policy"].policy_hash, result.patch_policy_hash)
        self.assertEqual(evidence["barrier"].barrier_hash, result.patch_barrier_hash)
        self.assertEqual(("runtime/patches/controlled_patch_apply.py",), result.target_paths)
        self.assertIn("step-24-controlled-patch-apply-regression", self.check_ids(result))
        self.assertIn("compileall-runtime-tests", self.check_ids(result))
        self.assertTrue(all(isinstance(check.command, (str, type(None))) for check in result.checks))

    def test_plan_hash_and_canonical_json_are_deterministic(self):
        evidence = self.evidence("runtime/patches/post_patch_verification_plan.py")

        first = self.plan(evidence)
        second = self.plan(evidence)
        left = {"b": {"z": 1, "a": 2}, "a": [3, {"d": 4, "c": 5}]}
        right = {"a": [3, {"c": 5, "d": 4}], "b": {"a": 2, "z": 1}}

        self.assertEqual(first.plan_hash, second.plan_hash)
        self.assertEqual(first.plan.to_dict(), second.plan.to_dict())
        self.assertEqual(canonical_post_patch_verification_plan_json(left), canonical_post_patch_verification_plan_json(right))
        self.assertEqual(compute_post_patch_verification_plan_hash(left), compute_post_patch_verification_plan_hash(right))

    def test_changing_meaningful_hash_inputs_changes_plan_hash(self):
        evidence = self.evidence("docs/hash-plan.md")
        ready = self.plan(evidence)
        changed_apply = self.plan({**evidence, "apply": replace(evidence["apply"], apply_hash="a" * 64)})
        changed_preview = self.plan({**evidence, "preview": replace(evidence["preview"], preview_hash="b" * 64)})
        changed_policy = self.plan({**evidence, "policy": replace(evidence["policy"], policy_hash="c" * 64)})
        changed_barrier = self.plan({**evidence, "barrier": replace(evidence["barrier"].decision, barrier_hash="d" * 64)})

        self.assertNotEqual(ready.plan_hash, changed_apply.plan_hash)
        self.assertNotEqual(ready.plan_hash, changed_preview.plan_hash)
        self.assertNotEqual(ready.plan_hash, changed_policy.plan_hash)
        self.assertNotEqual(ready.plan_hash, changed_barrier.plan_hash)

    def test_missing_required_inputs_block(self):
        evidence = self.evidence("docs/missing-plan.md")
        cases = {
            "apply": ({**evidence, "apply": None}, POST_PATCH_VERIFICATION_BLOCKED_MISSING_APPLY),
            "preview": ({**evidence, "preview": None}, POST_PATCH_VERIFICATION_BLOCKED_MISSING_PREVIEW),
            "policy": ({**evidence, "policy": None}, POST_PATCH_VERIFICATION_BLOCKED_MISSING_POLICY),
            "barrier": ({**evidence, "barrier": None}, POST_PATCH_VERIFICATION_BLOCKED_MISSING_BARRIER),
        }

        for name, (case, reason_code) in cases.items():
            with self.subTest(name=name):
                result = self.plan(case)

                self.assertEqual(POST_PATCH_VERIFICATION_BLOCKED, result.status)
                self.assertEqual((reason_code,), result.reason_codes)

    def test_failed_and_partial_apply_results_block(self):
        evidence = self.evidence("docs/apply-state.md")
        failed = self.rehash_apply(
            replace(
                evidence["apply"],
                status=CONTROLLED_PATCH_BLOCKED,
                reason_code=CONTROLLED_PATCH_BLOCKED,
                patch_applied=False,
            )
        )
        partial = self.rehash_apply(
            replace(
                evidence["apply"],
                status=CONTROLLED_PATCH_PARTIAL,
                reason_code=CONTROLLED_PATCH_PARTIAL,
                partial_apply=True,
                patch_applied=False,
            )
        )

        failed_result = self.plan({**evidence, "apply": failed})
        partial_result = self.plan({**evidence, "apply": partial})

        self.assertEqual((POST_PATCH_VERIFICATION_BLOCKED_APPLY_FAILED,), failed_result.reason_codes)
        self.assertEqual((POST_PATCH_VERIFICATION_BLOCKED_PARTIAL_APPLY,), partial_result.reason_codes)

    def test_hash_binding_mismatches_block(self):
        evidence = self.evidence("docs/binding-plan.md")
        preview_mismatch = self.rehash_apply(replace(evidence["apply"], patch_preview_hash="a" * 64))
        policy_mismatch = self.rehash_apply(replace(evidence["apply"], patch_policy_hash="b" * 64))
        barrier_mismatch = self.rehash_apply(replace(evidence["apply"], patch_barrier_hash="c" * 64))
        bad_apply_hash = replace(evidence["apply"], apply_hash="d" * 64)

        cases = {
            "preview": (preview_mismatch, POST_PATCH_VERIFICATION_BLOCKED_PREVIEW_HASH_MISMATCH),
            "policy": (policy_mismatch, POST_PATCH_VERIFICATION_BLOCKED_POLICY_HASH_MISMATCH),
            "barrier": (barrier_mismatch, POST_PATCH_VERIFICATION_BLOCKED_BARRIER_HASH_MISMATCH),
            "apply": (bad_apply_hash, POST_PATCH_VERIFICATION_BLOCKED_APPLY_HASH_MISMATCH),
        }

        for name, (apply_result, reason_code) in cases.items():
            with self.subTest(name=name):
                result = self.plan({**evidence, "apply": apply_result})

                self.assertEqual(POST_PATCH_VERIFICATION_BLOCKED, result.status)
                self.assertEqual((reason_code,), result.reason_codes)

    def test_target_and_content_hash_mismatches_block(self):
        evidence = self.evidence("docs/content-plan.md")
        target_mismatch = self.rehash_apply(replace(evidence["apply"], target_paths=("docs/other.md",)))
        tampered_file = replace(evidence["apply"].file_results[0], proposed_sha256="e" * 64)
        content_mismatch = self.rehash_apply(replace(evidence["apply"], file_results=(tampered_file,)))

        target_result = self.plan({**evidence, "apply": target_mismatch})
        content_result = self.plan({**evidence, "apply": content_mismatch})

        self.assertEqual((POST_PATCH_VERIFICATION_BLOCKED_TARGET_MISMATCH,), target_result.reason_codes)
        self.assertEqual((POST_PATCH_VERIFICATION_BLOCKED_CONTENT_HASH_MISMATCH,), content_result.reason_codes)

    def test_authority_like_fields_true_block_and_result_authority_fields_are_false(self):
        evidence = self.evidence("docs/authority-plan.md")
        tainted_apply = evidence["apply"]
        object.__setattr__(tainted_apply, "can_execute", True)

        blocked = self.plan({**evidence, "apply": tainted_apply})
        ready = self.plan(self.evidence("docs/authority-ready.md"))

        self.assertEqual((POST_PATCH_VERIFICATION_BLOCKED_AUTHORITY_CLAIM,), blocked.reason_codes)
        for result in (blocked, ready):
            for field_name in self.authority_fields():
                self.assertIs(False, getattr(result, field_name))
                self.assertIs(False, result.to_dict()[field_name])
        for field_name in self.authority_fields():
            self.assertIs(False, ready.plan.to_dict()[field_name])

    def test_check_selection_for_runtime_tests_patch_safety_provider_docs_and_multifile(self):
        runtime = self.plan(self.evidence("runtime/core/example.py"))
        tests = self.plan(self.evidence("tests/test_post_patch_verification_plan_1a.py"))
        patch = self.plan(self.evidence("runtime/patches/post_patch_verification_plan.py"))
        safety = self.plan(self.evidence("runtime/control_write.py"))
        provider = self.plan(self.evidence("runtime/providers/critic.py"))
        docs = self.plan(self.evidence("docs/only.md"))
        multi = self.plan(self.evidence("docs/a.md", "docs/b.md"))

        self.assertIn("compileall-runtime-tests", self.check_ids(runtime))
        self.assertIn("full-unittest-discovery", self.check_ids(runtime))
        self.assertIn("focused-tests-test_post_patch_verification_plan_1a", self.check_ids(tests))
        for check_id in (
            "step-21-patch-preview-regression",
            "step-22-patch-policy-regression",
            "step-23-human-patch-barrier-regression",
            "step-24-controlled-patch-apply-regression",
        ):
            self.assertIn(check_id, self.check_ids(patch))
        for check_id in (
            "step-12-authority-bypass-regression",
            "step-13-durable-ledger-regression",
            "step-14-static-boundary-regression",
            "step-15-kill-switch-regression",
            "step-16-workspace-guard-regression",
            "step-17-full-chain-fail-closed-regression",
        ):
            self.assertIn(check_id, self.check_ids(safety))
        self.assertIn("provider-critic-regression", self.check_ids(provider))
        self.assertIn("provider-e-inert-critic-regression", self.check_ids(provider))
        self.assertIn("docs-only-human-review", self.check_ids(docs))
        self.assertIn("diff-check-style", self.check_ids(docs))
        self.assertIn("full-unittest-discovery", self.check_ids(multi))

    def test_high_risk_policy_finding_includes_static_boundary_check_metadata(self):
        evidence = self.evidence("runtime/control_write.py")
        self.assertEqual(PATCH_POLICY_NEEDS_REVIEW, evidence["policy"].status)

        result = self.plan(evidence)

        self.assertIn("static-capability-boundary-check", self.check_ids(result))

    def test_verification_checks_are_metadata_only_and_cannot_satisfy_future_gates(self):
        result = self.plan(self.evidence("runtime/patches/post_patch_verification_plan.py"))
        payload = result.to_dict()

        self.assertEqual(POST_PATCH_VERIFICATION_READY, result.status)
        self.assertNotIn("gate_result", payload)
        self.assertNotIn("artifact_hash", payload)
        self.assertNotIn("packet_hash", payload)
        self.assertNotIn("writes_allowed", payload)
        self.assertNotIn("workspace_guard_allowed", payload)
        for check in result.checks:
            self.assertIsInstance(check.command, (str, type(None)))
            self.assertIsInstance(check.test_target, (str, type(None)))
            self.assertFalse(hasattr(check, "execute"))
            self.assertFalse(hasattr(check, "run"))

    def test_plan_result_cannot_bypass_kill_switch_or_workspace_guard_failure(self):
        result = self.plan(self.evidence("docs/no-bypass.md"))
        payload = result.to_dict()

        self.assertEqual(POST_PATCH_VERIFICATION_READY, result.status)
        self.assertNotIn("kill_switch_override", payload)
        self.assertNotIn("workspace_guard_override", payload)
        self.assertNotIn("write_authorization", payload)
        self.assertNotIn("gate_result", payload)

    def test_static_no_new_capability_scan_includes_verification_plan_module(self):
        forbidden_import_prefixes = (
            "subprocess",
            "os",
            "socket",
            "webbrowser",
            "selenium",
            "playwright",
            "requests",
            "httpx",
            "git",
            "openai",
            "anthropic",
            "google.generativeai",
            "google.genai",
            "ollama",
            "pip",
            "venv",
            "runtime.providers.gateway",
            "runtime.execution",
            "runtime.control_write",
            "runtime.safety.sandbox_artifact_runner",
        )
        forbidden_calls = {
            "subprocess.run",
            "subprocess.Popen",
            "subprocess.call",
            "subprocess.check_call",
            "subprocess.check_output",
            "os.system",
            "os.popen",
            "Popen",
            "eval",
            "exec",
            "__import__",
            "open",
            "Path.write_text",
            "Path.read_text",
            "write_text",
            "read_text",
        }
        scan = scan_module(PLAN_MODULE)

        self.assertEqual(
            [],
            [module for module in scan["imports"] if matches_any_prefix(module, forbidden_import_prefixes)],
        )
        self.assertEqual([], [call for call in scan["calls"] if call in forbidden_calls])
        source = PLAN_MODULE.read_text(encoding="utf-8")
        self.assertNotIn("subprocess", source)
        self.assertNotIn("Popen", source)
        self.assertNotIn("requests", source)
        self.assertNotIn("httpx", source)
        self.assertNotIn("write_text", source)

    def evidence(self, *target_paths: str):
        edits = tuple(
            PatchFileEdit(
                target_path=path,
                proposed_content=f"updated content for {path}\n",
                original_content=f"original content for {path}\n",
            )
            for path in target_paths
        )
        preview_result = build_patch_preview(edits)
        preview = preview_result.patch_preview
        policy = check_patch_local_policy(preview)
        barrier = create_human_patch_barrier(
            decision_value=PATCH_DECISION_APPROVE,
            patch_preview=preview,
            patch_policy=policy,
            decision_id="decision-" + preview.preview_hash[:16],
            reviewer_id="tester",
            created_at="2026-06-27T08:43:00Z",
            reason="test approval evidence",
        )
        return {
            "preview": preview,
            "policy": policy,
            "barrier": barrier,
            "apply": self.apply_result(preview, policy, barrier),
        }

    def apply_result(self, preview, policy, barrier):
        file_results = tuple(
            ControlledPatchApplyFileResult(
                target_path=file_preview.target_path,
                operation=file_preview.operation,
                status=CONTROLLED_PATCH_FILE_APPLIED,
                reason_code=CONTROLLED_PATCH_FILE_APPLIED,
                reason="test controlled write metadata",
                proposed_sha256=file_preview.proposed_sha256,
                original_sha256=file_preview.original_sha256,
                artifact_path=file_preview.target_path,
                controlled_write_status="ARTIFACT_WRITTEN",
                write_attempted=True,
                artifact_write_occurred=True,
            )
            for file_preview in preview.files
        )
        result = ControlledPatchApplyResult(
            status=CONTROLLED_PATCH_APPLIED,
            apply_hash=None,
            patch_preview_hash=preview.preview_hash,
            patch_policy_hash=policy.policy_hash,
            patch_barrier_hash=barrier.barrier_hash,
            target_paths=preview.target_paths,
            file_results=file_results,
            reason_code=CONTROLLED_PATCH_APPLIED,
            reason="test apply metadata",
        )
        return self.rehash_apply(result)

    def rehash_apply(self, apply_result):
        material = {
            "schema_version": "AOIA_CONTROLLED_PATCH_APPLY_1A",
            "status": apply_result.status,
            "patch_preview_hash": apply_result.patch_preview_hash,
            "patch_policy_hash": apply_result.patch_policy_hash,
            "patch_barrier_hash": apply_result.patch_barrier_hash,
            "target_paths": list(apply_result.target_paths),
            "file_results": [item.to_dict() for item in apply_result.file_results],
            "reason_code": apply_result.reason_code,
        }
        return replace(apply_result, apply_hash=compute_controlled_patch_apply_hash(material))

    def plan(self, evidence):
        return build_post_patch_verification_plan(
            apply_result=evidence["apply"],
            patch_preview=evidence["preview"],
            patch_policy=evidence["policy"],
            human_patch_barrier=evidence["barrier"],
        )

    @staticmethod
    def check_ids(result: PostPatchVerificationPlanResult):
        return {check.check_id for check in result.checks}

    @staticmethod
    def authority_fields():
        return (
            "can_approve",
            "can_write",
            "can_execute",
            "can_commit",
            "can_push",
            "can_call_provider",
            "can_change_gate",
            "write_authority_granted",
            "execution_authority_granted",
            "provider_authority_granted",
        )


def scan_module(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    aliases: dict[str, str] = {}
    imports: list[str] = []
    calls: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
                aliases[alias.asname or alias.name.split(".", 1)[0]] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
            for alias in node.names:
                full_name = f"{node.module}.{alias.name}"
                imports.append(full_name)
                aliases[alias.asname or alias.name] = full_name
        elif isinstance(node, ast.Call):
            calls.append(call_name(node.func, aliases))
    return {"imports": tuple(imports), "calls": tuple(item for item in calls if item)}


def call_name(node: ast.AST, aliases: dict[str, str]) -> str:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        parts = attribute_parts(node)
        if not parts:
            return ""
        root = aliases.get(parts[0], parts[0])
        return ".".join((root, *parts[1:]))
    return ""


def attribute_parts(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, ast.Attribute):
        return (*attribute_parts(node.value), node.attr)
    return ()


def matches_any_prefix(module_name: str, prefixes: tuple[str, ...]) -> bool:
    return any(module_name == prefix or module_name.startswith(prefix + ".") for prefix in prefixes)


if __name__ == "__main__":
    unittest.main()
