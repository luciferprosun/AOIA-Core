from __future__ import annotations

import ast
import subprocess
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from runtime.patches.controlled_patch_apply import (
    CONTROLLED_PATCH_APPLIED,
    CONTROLLED_PATCH_FILE_APPLIED,
    ControlledPatchApplyFileResult,
    ControlledPatchApplyResult,
    compute_controlled_patch_apply_hash,
)
from runtime.patches.patch_barrier import PATCH_DECISION_APPROVE, create_human_patch_barrier
from runtime.patches.patch_policy import check_patch_local_policy
from runtime.patches.patch_preview import PatchFileEdit, build_patch_preview
from runtime.patches.post_patch_controlled_test_integration import (
    COMMAND_KIND_COMPILEALL,
    COMMAND_KIND_UNITTEST_DISCOVER,
    COMMAND_KIND_UNITTEST_FOCUSED,
    CONTROLLED_VERIFICATION_BLOCKED,
    CONTROLLED_VERIFICATION_BLOCKED_APPLY_HASH_MISMATCH,
    CONTROLLED_VERIFICATION_BLOCKED_AUTHORITY_CLAIM,
    CONTROLLED_VERIFICATION_BLOCKED_BARRIER_HASH_MISMATCH,
    CONTROLLED_VERIFICATION_BLOCKED_CHECK_METADATA_MISMATCH,
    CONTROLLED_VERIFICATION_BLOCKED_CHECK_NOT_IN_PLAN,
    CONTROLLED_VERIFICATION_BLOCKED_MALFORMED_PLAN,
    CONTROLLED_VERIFICATION_BLOCKED_MISSING_PLAN,
    CONTROLLED_VERIFICATION_BLOCKED_OPERATOR_APPROVAL,
    CONTROLLED_VERIFICATION_BLOCKED_PLAN_HASH_MISMATCH,
    CONTROLLED_VERIFICATION_BLOCKED_PLAN_NOT_READY,
    CONTROLLED_VERIFICATION_BLOCKED_POLICY_HASH_MISMATCH,
    CONTROLLED_VERIFICATION_BLOCKED_PREVIEW_HASH_MISMATCH,
    CONTROLLED_VERIFICATION_BLOCKED_UNSAFE_COMMAND,
    CONTROLLED_VERIFICATION_BLOCKED_UNSAFE_TEST_TARGET,
    CONTROLLED_VERIFICATION_BLOCKED_UNSUPPORTED_CHECK_KIND,
    CONTROLLED_VERIFICATION_BLOCKED_WORKSPACE_GUARD,
    CONTROLLED_VERIFICATION_CHECK_FAILED,
    CONTROLLED_VERIFICATION_CHECK_TIMEOUT,
    CONTROLLED_VERIFICATION_FAIL,
    CONTROLLED_VERIFICATION_PASS,
    CONTROLLED_VERIFICATION_TIMEOUT,
    ControlledVerificationRunRequest,
    canonical_controlled_verification_json,
    compute_controlled_verification_hash,
    run_controlled_post_patch_verification,
)
from runtime.patches.post_patch_verification_plan import (
    CHECK_KIND_COMPILE,
    CHECK_KIND_REVIEW,
    CHECK_KIND_TEST,
    POST_PATCH_VERIFICATION_BLOCKED,
    PostPatchVerificationCheck,
    PostPatchVerificationPlan,
    build_post_patch_verification_plan,
    compute_post_patch_verification_plan_hash,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
STEP26_MODULE = REPO_ROOT / "runtime" / "patches" / "post_patch_controlled_test_integration.py"
PATCH_METADATA_MODULES = (
    REPO_ROOT / "runtime" / "patches" / "patch_preview.py",
    REPO_ROOT / "runtime" / "patches" / "patch_policy.py",
    REPO_ROOT / "runtime" / "patches" / "patch_barrier.py",
    REPO_ROOT / "runtime" / "patches" / "post_patch_verification_plan.py",
)


class PostPatchControlledTestIntegration1ATests(unittest.TestCase):
    def test_ready_plan_can_run_allowlisted_compileall_check(self):
        plan = self.plan_for("runtime/patches/post_patch_verification_plan.py")
        completed = subprocess.CompletedProcess(args=(sys.executable,), returncode=0, stdout="compile ok", stderr="")
        with patch("runtime.patches.post_patch_controlled_test_integration.subprocess.run", return_value=completed) as run_mock:
            result = self.execute_plan(plan, "compileall-runtime-tests")

        self.assertEqual(CONTROLLED_VERIFICATION_PASS, result.status)
        self.assertEqual(COMMAND_KIND_COMPILEALL, result.check_results[0].command_kind)
        self.assertEqual((sys.executable, "-m", "compileall", "runtime", "tests"), run_mock.call_args.args[0])
        self.assertIs(run_mock.call_args.kwargs["shell"], False)
        self.assertEqual(str(REPO_ROOT), run_mock.call_args.kwargs["cwd"])
        self.assertEqual({"PYTHONPATH": "runtime:.", "PYTHONNOUSERSITE": "1"}, run_mock.call_args.kwargs["env"])

    def test_ready_plan_can_run_allowlisted_focused_unittest_check(self):
        plan = self.plan_for("tests/test_post_patch_verification_plan_1a.py")
        check_id = "focused-tests-test_post_patch_verification_plan_1a"
        completed = subprocess.CompletedProcess(args=(sys.executable,), returncode=0, stdout="focused ok", stderr="")
        with patch("runtime.patches.post_patch_controlled_test_integration.subprocess.run", return_value=completed) as run_mock:
            result = self.execute_plan(plan, check_id)

        self.assertEqual(CONTROLLED_VERIFICATION_PASS, result.status)
        self.assertEqual(COMMAND_KIND_UNITTEST_FOCUSED, result.check_results[0].command_kind)
        self.assertEqual((sys.executable, "-m", "unittest", "tests.test_post_patch_verification_plan_1a", "-v"), run_mock.call_args.args[0])

    def test_ready_plan_can_run_allowlisted_full_unittest_discovery_check(self):
        plan = self.plan_for("runtime/patches/post_patch_verification_plan.py")
        completed = subprocess.CompletedProcess(args=(sys.executable,), returncode=0, stdout="full ok", stderr="")
        with patch("runtime.patches.post_patch_controlled_test_integration.subprocess.run", return_value=completed) as run_mock:
            result = self.execute_plan(plan, "full-unittest-discovery")

        self.assertEqual(CONTROLLED_VERIFICATION_PASS, result.status)
        self.assertEqual(COMMAND_KIND_UNITTEST_DISCOVER, result.check_results[0].command_kind)
        self.assertEqual((sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test*.py", "-v"), run_mock.call_args.args[0])

    def test_run_hash_and_canonical_json_are_deterministic(self):
        plan = self.plan_for("runtime/patches/post_patch_verification_plan.py")
        completed = subprocess.CompletedProcess(args=(sys.executable,), returncode=0, stdout="stable", stderr="")
        with patch("runtime.patches.post_patch_controlled_test_integration.subprocess.run", return_value=completed):
            first = self.execute_plan(plan, "compileall-runtime-tests")
            second = self.execute_plan(plan, "compileall-runtime-tests")

        left = {"b": {"z": 1, "a": 2}, "a": [3, {"d": 4, "c": 5}]}
        right = {"a": [3, {"c": 5, "d": 4}], "b": {"a": 2, "z": 1}}
        self.assertEqual(first.run_hash, second.run_hash)
        self.assertEqual(canonical_controlled_verification_json(left), canonical_controlled_verification_json(right))
        self.assertEqual(compute_controlled_verification_hash(left), compute_controlled_verification_hash(right))

    def test_missing_malformed_not_ready_and_unapproved_plan_blocks(self):
        ready = self.plan_for("docs/no-run.md")
        blocked_plan = replace(ready, status=POST_PATCH_VERIFICATION_BLOCKED)
        cases = {
            "missing": (replace(self.request(ready), verification_plan=None), CONTROLLED_VERIFICATION_BLOCKED_MISSING_PLAN),
            "malformed": ({}, CONTROLLED_VERIFICATION_BLOCKED_MALFORMED_PLAN),
            "not_ready": (self.request(blocked_plan), CONTROLLED_VERIFICATION_BLOCKED_PLAN_NOT_READY),
            "unapproved": (replace(self.request(ready), operator_approved=False), CONTROLLED_VERIFICATION_BLOCKED_OPERATOR_APPROVAL),
        }
        for name, (request, reason_code) in cases.items():
            with self.subTest(name=name):
                result = run_controlled_post_patch_verification(request)

                self.assertEqual(CONTROLLED_VERIFICATION_BLOCKED, result.status)
                self.assertEqual((reason_code,), result.reason_codes)

    def test_hash_binding_mismatches_block(self):
        plan = self.plan_for("runtime/patches/post_patch_verification_plan.py")
        cases = {
            "plan": (replace(self.request(plan), expected_plan_hash="a" * 64), CONTROLLED_VERIFICATION_BLOCKED_PLAN_HASH_MISMATCH),
            "apply": (replace(self.request(plan), expected_apply_hash="b" * 64), CONTROLLED_VERIFICATION_BLOCKED_APPLY_HASH_MISMATCH),
            "preview": (replace(self.request(plan), expected_patch_preview_hash="c" * 64), CONTROLLED_VERIFICATION_BLOCKED_PREVIEW_HASH_MISMATCH),
            "policy": (replace(self.request(plan), expected_patch_policy_hash="d" * 64), CONTROLLED_VERIFICATION_BLOCKED_POLICY_HASH_MISMATCH),
            "barrier": (replace(self.request(plan), expected_patch_barrier_hash="e" * 64), CONTROLLED_VERIFICATION_BLOCKED_BARRIER_HASH_MISMATCH),
        }
        for name, (request, reason_code) in cases.items():
            with self.subTest(name=name):
                result = run_controlled_post_patch_verification(request)

                self.assertEqual(CONTROLLED_VERIFICATION_BLOCKED, result.status)
                self.assertEqual((reason_code,), result.reason_codes)

    def test_requested_check_not_in_plan_and_changed_check_metadata_block(self):
        plan = self.plan_for("runtime/patches/post_patch_verification_plan.py")
        tampered = replace(plan, checks=(replace(plan.checks[0], reason="changed after plan"),))

        missing = self.execute_plan(plan, "missing-check")
        changed = self.execute_plan(tampered, tampered.checks[0].check_id)

        self.assertEqual((CONTROLLED_VERIFICATION_BLOCKED_CHECK_NOT_IN_PLAN,), missing.reason_codes)
        self.assertEqual((CONTROLLED_VERIFICATION_BLOCKED_CHECK_METADATA_MISMATCH,), changed.reason_codes)

    def test_stale_replayed_plan_for_different_patch_blocks(self):
        plan_a = self.plan_for("runtime/patches/post_patch_verification_plan.py")
        plan_b = self.plan_for("tests/test_post_patch_verification_plan_1a.py")
        request = replace(
            self.request(plan_a),
            expected_apply_hash=plan_b.apply_hash,
            expected_patch_preview_hash=plan_b.patch_preview_hash,
            expected_patch_policy_hash=plan_b.patch_policy_hash,
            expected_patch_barrier_hash=plan_b.patch_barrier_hash,
        )

        result = run_controlled_post_patch_verification(request)

        self.assertEqual(CONTROLLED_VERIFICATION_BLOCKED, result.status)
        self.assertEqual((CONTROLLED_VERIFICATION_BLOCKED_APPLY_HASH_MISMATCH,), result.reason_codes)

    def test_unsupported_unknown_review_and_unsafe_command_families_block_before_execution(self):
        base = self.plan_for("runtime/patches/post_patch_verification_plan.py")
        cases = {
            "unknown": (
                self.rehash_with_check(base, replace(base.checks[0], check_kind="mystery")),
                CONTROLLED_VERIFICATION_BLOCKED_UNSUPPORTED_CHECK_KIND,
            ),
            "review": (
                self.rehash_with_check(base, replace(base.checks[0], check_kind=CHECK_KIND_REVIEW, command=None, test_target="human-review:only")),
                CONTROLLED_VERIFICATION_BLOCKED_UNSAFE_COMMAND,
            ),
            "raw_shell": (
                self.rehash_with_check(base, replace(base.checks[0], command="bash -c 'echo no'")),
                CONTROLLED_VERIFICATION_BLOCKED_UNSAFE_COMMAND,
            ),
            "metachar": (
                self.rehash_with_check(base, replace(base.checks[0], command="python3 -m compileall runtime tests; git status")),
                CONTROLLED_VERIFICATION_BLOCKED_UNSAFE_COMMAND,
            ),
            "git": (
                self.rehash_with_check(base, replace(base.checks[0], command="git status")),
                CONTROLLED_VERIFICATION_BLOCKED_UNSAFE_COMMAND,
            ),
            "package": (
                self.rehash_with_check(base, replace(base.checks[0], command="pip install pytest")),
                CONTROLLED_VERIFICATION_BLOCKED_UNSAFE_COMMAND,
            ),
            "provider_network_browser": (
                self.rehash_with_check(base, replace(base.checks[0], command="python3 -m unittest tests.test_openai_provider -v")),
                CONTROLLED_VERIFICATION_BLOCKED_UNSAFE_COMMAND,
            ),
            "env_secret": (
                self.rehash_with_check(base, replace(base.checks[0], command="PYTHONPATH=runtime:. python3 -m unittest tests.test_token_secret -v")),
                CONTROLLED_VERIFICATION_BLOCKED_UNSAFE_COMMAND,
            ),
        }
        for name, (plan, reason_code) in cases.items():
            with self.subTest(name=name), patch("runtime.patches.post_patch_controlled_test_integration.subprocess.run") as run_mock:
                result = self.execute_plan(plan, plan.checks[0].check_id)

                self.assertEqual(CONTROLLED_VERIFICATION_BLOCKED, result.status)
                self.assertEqual((reason_code,), result.reason_codes)
                run_mock.assert_not_called()

    def test_unsafe_traversal_and_absolute_test_targets_block(self):
        base = self.plan_for("tests/test_post_patch_verification_plan_1a.py")
        cases = {
            "unsafe": "runtime.not_tests",
            "traversal": "tests..evil",
            "absolute": "/tests.test_post_patch_verification_plan_1a",
        }
        for name, target in cases.items():
            with self.subTest(name=name):
                bad_check = replace(
                    base.checks[0],
                    check_kind=CHECK_KIND_TEST,
                    test_target=target,
                    command=f"PYTHONPATH=runtime:. python3 -m unittest {target} -v",
                )
                plan = self.rehash_with_check(base, bad_check)
                result = self.execute_plan(plan, bad_check.check_id)

                self.assertEqual(CONTROLLED_VERIFICATION_BLOCKED, result.status)
                self.assertEqual((CONTROLLED_VERIFICATION_BLOCKED_UNSAFE_TEST_TARGET,), result.reason_codes)

    def test_workspace_guard_failure_blocks(self):
        plan = self.plan_for("runtime/patches/post_patch_verification_plan.py")

        result = run_controlled_post_patch_verification(replace(self.request(plan), workspace_root="relative"))

        self.assertEqual(CONTROLLED_VERIFICATION_BLOCKED, result.status)
        self.assertEqual((CONTROLLED_VERIFICATION_BLOCKED_WORKSPACE_GUARD,), result.reason_codes)

    def test_timeout_output_bounds_and_failing_command_are_stable(self):
        plan = self.plan_for("runtime/patches/post_patch_verification_plan.py")
        timeout = subprocess.TimeoutExpired(cmd=(sys.executable,), timeout=1, output="x" * 200, stderr="y" * 200)
        with patch("runtime.patches.post_patch_controlled_test_integration.subprocess.run", side_effect=timeout):
            timed_out = run_controlled_post_patch_verification(
                replace(self.request(plan, "compileall-runtime-tests"), timeout_seconds=1, max_output_bytes=40)
            )
        failed_process = subprocess.CompletedProcess(args=(sys.executable,), returncode=2, stdout="bad", stderr="failed")
        with patch("runtime.patches.post_patch_controlled_test_integration.subprocess.run", return_value=failed_process):
            failed = self.execute_plan(plan, "compileall-runtime-tests")

        self.assertEqual(CONTROLLED_VERIFICATION_FAIL, timed_out.status)
        self.assertEqual(CONTROLLED_VERIFICATION_CHECK_TIMEOUT, timed_out.check_results[0].status)
        self.assertEqual(CONTROLLED_VERIFICATION_TIMEOUT, timed_out.check_results[0].reason_code)
        self.assertTrue(timed_out.check_results[0].timeout_expired)
        self.assertLessEqual(len(timed_out.check_results[0].stdout_preview.encode("utf-8")), 40)
        self.assertLessEqual(len(timed_out.check_results[0].stderr_preview.encode("utf-8")), 40)
        self.assertEqual(CONTROLLED_VERIFICATION_FAIL, failed.status)
        self.assertEqual((CONTROLLED_VERIFICATION_CHECK_FAILED,), failed.reason_codes)

    def test_result_authority_fields_false_and_pass_cannot_satisfy_future_authority(self):
        plan = self.plan_for("runtime/patches/post_patch_verification_plan.py")
        completed = subprocess.CompletedProcess(args=(sys.executable,), returncode=0, stdout="ok", stderr="")
        with patch("runtime.patches.post_patch_controlled_test_integration.subprocess.run", return_value=completed):
            result = self.execute_plan(plan, "compileall-runtime-tests")

        self.assertEqual(CONTROLLED_VERIFICATION_PASS, result.status)
        payload = result.to_dict()
        for field_name in self.authority_fields():
            self.assertIs(False, getattr(result, field_name))
            self.assertIs(False, payload[field_name])
        for forbidden in ("commit_authority", "push_authority", "gate_result", "artifact_hash", "packet_hash", "kill_switch_override", "workspace_guard_override"):
            self.assertNotIn(forbidden, payload)

    def test_authority_like_plan_fields_true_block(self):
        plan = self.plan_for("runtime/patches/post_patch_verification_plan.py")
        object.__setattr__(plan, "can_execute", True)

        result = self.execute_plan(plan, "compileall-runtime-tests")

        self.assertEqual(CONTROLLED_VERIFICATION_BLOCKED, result.status)
        self.assertEqual((CONTROLLED_VERIFICATION_BLOCKED_AUTHORITY_CLAIM,), result.reason_codes)

    def test_shell_true_is_never_used(self):
        plan = self.plan_for("runtime/patches/post_patch_verification_plan.py")
        completed = subprocess.CompletedProcess(args=(sys.executable,), returncode=0, stdout="ok", stderr="")
        with patch("runtime.patches.post_patch_controlled_test_integration.subprocess.run", return_value=completed) as run_mock:
            self.execute_plan(plan, "compileall-runtime-tests")

        self.assertIs(run_mock.call_args.kwargs["shell"], False)
        self.assertNotIn("shell=True", STEP26_MODULE.read_text(encoding="utf-8"))

    def test_subprocess_import_is_allowed_only_in_step26_patch_execution_module(self):
        step26_scan = scan_module(STEP26_MODULE)
        self.assertIn("subprocess", step26_scan["imports"])
        self.assertNotIn("subprocess.run", step26_scan["calls"])
        self.assertIn(
            "runtime.safety.bounded_subprocess.run_bounded_subprocess",
            step26_scan["calls"],
        )
        self.assertNotIn("subprocess.Popen", step26_scan["calls"])
        forbidden = ("subprocess", "runtime.execution", "runtime.providers.gateway", "requests", "httpx", "webbrowser", "playwright", "selenium", "git")
        for path in PATCH_METADATA_MODULES:
            with self.subTest(path=path.name):
                scan = scan_module(path)
                self.assertEqual([], [module for module in scan["imports"] if matches_any_prefix(module, forbidden)])

    def plan_for(self, *target_paths: str):
        evidence = self.evidence(*target_paths)
        return build_post_patch_verification_plan(
            apply_result=evidence["apply"],
            patch_preview=evidence["preview"],
            patch_policy=evidence["policy"],
            human_patch_barrier=evidence["barrier"],
        )

    def evidence(self, *target_paths: str):
        edits = tuple(
            PatchFileEdit(
                target_path=path,
                proposed_content=f"updated content for {path}\n",
                original_content=f"original content for {path}\n",
            )
            for path in target_paths
        )
        preview = build_patch_preview(edits).patch_preview
        policy = check_patch_local_policy(preview)
        barrier = create_human_patch_barrier(
            decision_value=PATCH_DECISION_APPROVE,
            patch_preview=preview,
            patch_policy=policy,
            decision_id="decision-" + preview.preview_hash[:16],
            reviewer_id="tester",
            created_at="2026-06-27T09:55:00Z",
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

    def request(self, plan, *check_ids):
        selected = check_ids or (plan.checks[0].check_id,)
        return ControlledVerificationRunRequest(
            verification_plan=plan,
            workspace_root=str(REPO_ROOT),
            requested_check_ids=selected,
            expected_plan_hash=plan.plan_hash,
            expected_apply_hash=plan.apply_hash,
            expected_patch_preview_hash=plan.patch_preview_hash,
            expected_patch_policy_hash=plan.patch_policy_hash,
            expected_patch_barrier_hash=plan.patch_barrier_hash,
            operator_approved=True,
        )

    def execute_plan(self, plan, *check_ids):
        return run_controlled_post_patch_verification(self.request(plan, *check_ids))

    def rehash_with_check(self, plan_result, check):
        checks = (check,)
        material = {
            "schema_version": "AOIA_POST_PATCH_VERIFICATION_PLAN_1A",
            "status": plan_result.plan.status,
            "apply_hash": plan_result.plan.apply_hash,
            "patch_preview_hash": plan_result.plan.patch_preview_hash,
            "patch_policy_hash": plan_result.plan.patch_policy_hash,
            "patch_barrier_hash": plan_result.plan.patch_barrier_hash,
            "target_paths": list(plan_result.plan.target_paths),
            "applied_content_hashes": [list(item) for item in plan_result.plan.applied_content_hashes],
            "policy_status": plan_result.plan.policy_status,
            "apply_status": plan_result.plan.apply_status,
            "scope_classification": plan_result.plan.scope_classification,
            "checks": [item.to_dict() for item in checks],
            "reason_codes": list(plan_result.plan.reason_codes),
            "risk_flags": list(plan_result.plan.risk_flags),
        }
        plan_hash = compute_post_patch_verification_plan_hash(material)
        plan = replace(
            plan_result.plan,
            plan_hash=plan_hash,
            checks=checks,
        )
        return replace(
            plan_result,
            plan_hash=plan_hash,
            checks=checks,
            plan=plan,
        )

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
