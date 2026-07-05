from __future__ import annotations

import ast
import tempfile
import unittest
from dataclasses import dataclass, replace
from pathlib import Path

from runtime.package_ops.controlled_package_install import (
    CONTROLLED_PACKAGE_INSTALL_BLOCKED,
    CONTROLLED_PACKAGE_INSTALL_BLOCKED_APT_UNSUPPORTED,
    CONTROLLED_PACKAGE_INSTALL_BLOCKED_AUTHORITY_CLAIM,
    CONTROLLED_PACKAGE_INSTALL_BLOCKED_BARRIER_HASH_MISMATCH,
    CONTROLLED_PACKAGE_INSTALL_BLOCKED_BARRIER_SCOPE_MISMATCH,
    CONTROLLED_PACKAGE_INSTALL_BLOCKED_BARRIER_STALE,
    CONTROLLED_PACKAGE_INSTALL_BLOCKED_CURRENT_STATE_MISMATCH,
    CONTROLLED_PACKAGE_INSTALL_BLOCKED_EXECUTION_FAILED,
    CONTROLLED_PACKAGE_INSTALL_BLOCKED_HASH_MISMATCH,
    CONTROLLED_PACKAGE_INSTALL_BLOCKED_MALFORMED_EVIDENCE,
    CONTROLLED_PACKAGE_INSTALL_BLOCKED_NON_OFFLINE,
    CONTROLLED_PACKAGE_INSTALL_BLOCKED_UNSAFE_SOURCE,
    CONTROLLED_PACKAGE_INSTALL_BLOCKED_UNSAFE_TARGET,
    CONTROLLED_PACKAGE_INSTALL_COMPLETED,
    CONTROLLED_PACKAGE_INSTALL_FAILED,
    CONTROLLED_PACKAGE_INSTALL_REASON_COMPLETED_OFFLINE_SANDBOX,
    PackageInstallCurrentState,
    PackageInstallHumanBarrier,
    compute_package_install_barrier_hash,
    create_package_install_human_barrier,
    execute_controlled_package_install,
)
from runtime.package_ops.package_install_proposal import (
    PackageInstallProposalRequest,
    compute_package_install_request_hash,
    propose_package_install,
)


RUNTIME_FILE = Path(__file__).resolve().parents[1] / "runtime" / "package_ops" / "controlled_package_install.py"


class ControlledPackageInstall1ATests(unittest.TestCase):
    def test_valid_pip_install_uses_offline_temp_venv_only(self):
        with self.evidence() as evidence:
            runner = FakeRunner(exit_code=0, stdout="installed")
            result = execute_controlled_package_install(
                proposal=evidence.proposal_request,
                validation_result=evidence.validation_result,
                human_barrier=evidence.barrier,
                current_state=evidence.current_state,
                source_artifact_path=str(evidence.source),
                target_path=str(evidence.target),
                runner=runner,
                environment_builder=FakeVenvBuilder(),
            )

            self.assertEqual(CONTROLLED_PACKAGE_INSTALL_COMPLETED, result.status)
            self.assertEqual((CONTROLLED_PACKAGE_INSTALL_REASON_COMPLETED_OFFLINE_SANDBOX,), result.reason_codes)
            self.assertEqual(1, len(runner.calls))
            argv = runner.calls[0]["argv"]
            self.assertIn("-m", argv)
            self.assertIn("pip", argv)
            self.assertIn("--no-index", argv)
            self.assertIn("--no-deps", argv)
            self.assertNotIn("apt", argv)
            self.assertEqual(evidence.target, runner.calls[0]["cwd"])
            self.assert_metadata_only(result.to_dict(), attempted=True, completed=True)

    def test_valid_npm_install_uses_offline_temp_project_only(self):
        with self.evidence(ecosystem="npm", package_name="left-pad", version="1.3.0", source_name="left-pad-1.3.0.tgz") as evidence:
            runner = FakeRunner(exit_code=0)
            result = execute_controlled_package_install(
                proposal=evidence.proposal_request,
                validation_result=evidence.validation_result,
                human_barrier=evidence.barrier,
                current_state=evidence.current_state,
                source_artifact_path=str(evidence.source),
                target_path=str(evidence.target),
                runner=runner,
            )

            self.assertEqual(CONTROLLED_PACKAGE_INSTALL_COMPLETED, result.status)
            argv = runner.calls[0]["argv"]
            self.assertEqual("npm", argv[0])
            self.assertIn("--offline", argv)
            self.assertIn("--ignore-scripts", argv)
            self.assertIn("--no-save", argv)
            self.assertNotIn("apt", argv)
            self.assertTrue((evidence.target / "package.json").exists())
            self.assert_metadata_only(result.to_dict(), attempted=True, completed=True)

    def test_apt_proposal_is_recognized_but_execution_fails_closed(self):
        with self.evidence(ecosystem="apt", package_name="curl", version="8.5.0-2ubuntu10.6", source_name="curl.deb") as evidence:
            runner = FakeRunner(exit_code=0)
            result = execute_controlled_package_install(
                proposal=evidence.proposal_request,
                validation_result=evidence.validation_result,
                human_barrier=evidence.barrier,
                current_state=evidence.current_state,
                source_artifact_path=str(evidence.source),
                target_path=str(evidence.target),
                runner=runner,
            )

            self.assertEqual(CONTROLLED_PACKAGE_INSTALL_BLOCKED, result.status)
            self.assertIn(CONTROLLED_PACKAGE_INSTALL_BLOCKED_APT_UNSUPPORTED, result.reason_codes)
            self.assertEqual([], runner.calls)
            self.assert_metadata_only(result.to_dict())

    def test_missing_or_malformed_evidence_fails_closed(self):
        with self.evidence() as evidence:
            cases = (
                {"proposal": None},
                {"validation_result": None},
                {"human_barrier": None},
                {"current_state": None},
            )
            for override in cases:
                kwargs = {
                    "proposal": evidence.proposal_request,
                    "validation_result": evidence.validation_result,
                    "human_barrier": evidence.barrier,
                    "current_state": evidence.current_state,
                    "source_artifact_path": str(evidence.source),
                    "target_path": str(evidence.target),
                    "runner": FakeRunner(),
                    "environment_builder": FakeVenvBuilder(),
                }
                kwargs.update(override)
                with self.subTest(override=override):
                    result = execute_controlled_package_install(**kwargs)

                    self.assertEqual(CONTROLLED_PACKAGE_INSTALL_BLOCKED, result.status)
                    self.assertIn(CONTROLLED_PACKAGE_INSTALL_BLOCKED_MALFORMED_EVIDENCE, result.reason_codes)

    def test_proposal_validation_hash_mismatch_fails_closed(self):
        with self.evidence() as evidence:
            changed_request = replace(evidence.proposal_request, reason="Changed reviewed reason.")
            changed_validation = replace(evidence.validation_result, proposal_hash="0" * 64)

            for proposal_request, validation in (
                (changed_request, evidence.validation_result),
                (evidence.proposal_request, changed_validation),
            ):
                with self.subTest(validation=validation.proposal_hash):
                    result = execute_controlled_package_install(
                        proposal=proposal_request,
                        validation_result=validation,
                        human_barrier=evidence.barrier,
                        current_state=evidence.current_state,
                        source_artifact_path=str(evidence.source),
                        target_path=str(evidence.target),
                        runner=FakeRunner(),
                        environment_builder=FakeVenvBuilder(),
                    )

                    self.assertEqual(CONTROLLED_PACKAGE_INSTALL_BLOCKED, result.status)
                    self.assertIn(CONTROLLED_PACKAGE_INSTALL_BLOCKED_HASH_MISMATCH, result.reason_codes)

    def test_barrier_hash_scope_and_ttl_are_enforced(self):
        with self.evidence() as evidence:
            wrong_hash = {**evidence.barrier.to_dict(), "barrier_hash": "1" * 64}
            wrong_scope = self.barrier(evidence, package_name="different")
            stale = self.barrier(evidence, approved_at=1, expires_at=9)

            cases = (
                (wrong_hash, CONTROLLED_PACKAGE_INSTALL_BLOCKED_BARRIER_HASH_MISMATCH),
                (wrong_scope, CONTROLLED_PACKAGE_INSTALL_BLOCKED_BARRIER_SCOPE_MISMATCH),
                (stale, CONTROLLED_PACKAGE_INSTALL_BLOCKED_BARRIER_STALE),
            )
            for barrier, reason in cases:
                with self.subTest(reason=reason):
                    result = execute_controlled_package_install(
                        proposal=evidence.proposal_request,
                        validation_result=evidence.validation_result,
                        human_barrier=barrier,
                        current_state=evidence.current_state,
                        source_artifact_path=str(evidence.source),
                        target_path=str(evidence.target),
                        runner=FakeRunner(),
                        environment_builder=FakeVenvBuilder(),
                    )

                    self.assertEqual(CONTROLLED_PACKAGE_INSTALL_BLOCKED, result.status)
                    self.assertIn(reason, result.reason_codes)

    def test_current_state_offline_and_sandbox_constraints_are_enforced(self):
        with self.evidence() as evidence:
            outside_source = evidence.root / "outside.whl"
            outside_source.write_text("outside", encoding="utf-8")
            outside_target = evidence.root / "outside-target"
            cases = (
                (
                    evidence.current_state,
                    str(outside_source),
                    str(evidence.target),
                    CONTROLLED_PACKAGE_INSTALL_BLOCKED_UNSAFE_SOURCE,
                ),
                (
                    evidence.current_state,
                    str(evidence.source),
                    str(outside_target),
                    CONTROLLED_PACKAGE_INSTALL_BLOCKED_UNSAFE_TARGET,
                ),
                (
                    replace(evidence.current_state, offline_mode=False),
                    str(evidence.source),
                    str(evidence.target),
                    CONTROLLED_PACKAGE_INSTALL_BLOCKED_NON_OFFLINE,
                ),
                (
                    replace(evidence.current_state, dependency_context_hash="e" * 64),
                    str(evidence.source),
                    str(evidence.target),
                    CONTROLLED_PACKAGE_INSTALL_BLOCKED_CURRENT_STATE_MISMATCH,
                ),
            )
            for state, source, target, reason in cases:
                with self.subTest(reason=reason):
                    result = execute_controlled_package_install(
                        proposal=evidence.proposal_request,
                        validation_result=evidence.validation_result,
                        human_barrier=evidence.barrier,
                        current_state=state,
                        source_artifact_path=source,
                        target_path=target,
                        runner=FakeRunner(),
                        environment_builder=FakeVenvBuilder(),
                    )

                    self.assertEqual(CONTROLLED_PACKAGE_INSTALL_BLOCKED, result.status)
                    self.assertIn(reason, result.reason_codes)

    def test_authority_claims_cannot_substitute_for_barrier(self):
        with self.evidence() as evidence:
            forged_barrier = {
                "approved": True,
                "safe": True,
                "can_install": True,
                "authority": True,
            }
            forced_barrier = replace(
                evidence.barrier,
                can_install=True,
                can_execute=True,
                gate_satisfied=True,
                human_barrier_satisfied=True,
                future_install_authorized=True,
            )

            malformed = execute_controlled_package_install(
                proposal=evidence.proposal_request,
                validation_result=evidence.validation_result,
                human_barrier=forged_barrier,
                current_state=evidence.current_state,
                source_artifact_path=str(evidence.source),
                target_path=str(evidence.target),
                runner=FakeRunner(),
                environment_builder=FakeVenvBuilder(),
            )
            self.assertEqual(CONTROLLED_PACKAGE_INSTALL_BLOCKED, malformed.status)
            self.assertIn(CONTROLLED_PACKAGE_INSTALL_BLOCKED_MALFORMED_EVIDENCE, malformed.reason_codes)

            result = execute_controlled_package_install(
                proposal=evidence.proposal_request,
                validation_result=evidence.validation_result,
                human_barrier=forced_barrier,
                current_state=evidence.current_state,
                source_artifact_path=str(evidence.source),
                target_path=str(evidence.target),
                runner=FakeRunner(exit_code=0),
                environment_builder=FakeVenvBuilder(),
            )
            self.assertEqual(CONTROLLED_PACKAGE_INSTALL_COMPLETED, result.status)
            self.assertFalse(forced_barrier.can_install)
            self.assertFalse(forced_barrier.gate_satisfied)
            self.assert_metadata_only(result.to_dict(), attempted=True, completed=True)

    def test_runner_failure_returns_failed_without_authorizing_future_installs(self):
        with self.evidence() as evidence:
            result = execute_controlled_package_install(
                proposal=evidence.proposal_request,
                validation_result=evidence.validation_result,
                human_barrier=evidence.barrier,
                current_state=evidence.current_state,
                source_artifact_path=str(evidence.source),
                target_path=str(evidence.target),
                runner=FakeRunner(exit_code=1, stderr="offline artifact rejected"),
                environment_builder=FakeVenvBuilder(),
            )

            self.assertEqual(CONTROLLED_PACKAGE_INSTALL_FAILED, result.status)
            self.assertIn(CONTROLLED_PACKAGE_INSTALL_BLOCKED_EXECUTION_FAILED, result.reason_codes)
            self.assert_metadata_only(result.to_dict(), attempted=True, completed=False)

    def test_result_hash_is_deterministic_and_changes_with_execution_evidence(self):
        with self.evidence() as evidence:
            first = execute_controlled_package_install(
                proposal=evidence.proposal_request,
                validation_result=evidence.validation_result,
                human_barrier=evidence.barrier,
                current_state=evidence.current_state,
                source_artifact_path=str(evidence.source),
                target_path=str(evidence.target),
                runner=FakeRunner(exit_code=0, stdout="same"),
                environment_builder=FakeVenvBuilder(),
            )
            second = execute_controlled_package_install(
                proposal=evidence.proposal_request,
                validation_result=evidence.validation_result,
                human_barrier=evidence.barrier,
                current_state=evidence.current_state,
                source_artifact_path=str(evidence.source),
                target_path=str(evidence.target),
                runner=FakeRunner(exit_code=0, stdout="same"),
                environment_builder=FakeVenvBuilder(),
            )
            changed = execute_controlled_package_install(
                proposal=evidence.proposal_request,
                validation_result=evidence.validation_result,
                human_barrier=evidence.barrier,
                current_state=evidence.current_state,
                source_artifact_path=str(evidence.source),
                target_path=str(evidence.target),
                runner=FakeRunner(exit_code=0, stdout="changed"),
                environment_builder=FakeVenvBuilder(),
            )

            self.assertEqual(first.result_hash, second.result_hash)
            self.assertNotEqual(first.result_hash, changed.result_hash)

    def test_module_static_surface_is_narrow_controlled_execution_only(self):
        source = RUNTIME_FILE.read_text(encoding="utf-8").casefold()
        scan = scan_module(RUNTIME_FILE)

        self.assertIn("subprocess", scan.imports)
        self.assertIn("subprocess.run", scan.calls)
        self.assertIn("venv", scan.imports)
        self.assertNotIn("subprocess.Popen", scan.calls)
        for forbidden_import in (
            "os",
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
            "runtime.human_decision_gated_artifact_write",
        ):
            self.assertNotIn(forbidden_import, scan.imports)
        for forbidden_text in (
            "shell=true",
            "os.environ",
            "getenv",
            "sudo",
            "apt install",
            "apt-get install",
            "curl ",
            "wget ",
            "api_key",
        ):
            self.assertNotIn(forbidden_text, source)

    def evidence(self, **overrides):
        return EvidenceContext(**overrides)

    def barrier(self, evidence, **overrides) -> PackageInstallHumanBarrier:
        values = {
            "proposal_hash": compute_package_install_request_hash(evidence.proposal_request),
            "validation_hash": evidence.validation_result.proposal_hash,
            "ecosystem": evidence.validation_result.ecosystem,
            "package_name": evidence.validation_result.package_name,
            "package_version": evidence.validation_result.version,
            "source": str(evidence.source),
            "target": str(evidence.target),
            "dependency_context_hash": evidence.current_state.dependency_context_hash,
            "target_environment_hash": evidence.current_state.target_environment_hash,
            "approved_by": "local-human-operator",
            "approval_reason": "Approve offline temporary sandbox package install only.",
            "approved_at": 10,
            "expires_at": 20,
        }
        values.update(overrides)
        return create_package_install_human_barrier(**values)

    def assert_metadata_only(self, data: dict, *, attempted: bool = False, completed: bool = False) -> None:
        self.assertEqual(attempted, data["sandbox_install_attempted"])
        self.assertEqual(completed, data["sandbox_install_completed"])
        self.assertEqual(attempted, data["package_manager_called"])
        self.assertEqual(attempted, data["subprocess_started"])
        for field_name in (
            "shell_invoked",
            "network_called",
            "package_registry_called",
            "apt_executed",
            "real_environment_modified",
            "dependency_file_modified",
            "provider_called",
            "browser_opened",
            "git_action_performed",
            "approval_created",
            "gate_satisfied",
            "human_barrier_satisfied",
            "can_install",
            "can_execute",
            "can_write",
            "can_push",
            "can_call_provider",
            "can_change_gate",
            "future_install_authorized",
        ):
            self.assertFalse(data[field_name])


@dataclass
class EvidenceContext:
    ecosystem: str = "pip"
    package_name: str = "samplepkg"
    version: str = "1.0.0"
    source_name: str = "samplepkg-1.0.0-py3-none-any.whl"

    def __enter__(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.artifacts = self.root / "artifacts"
        self.sandbox = self.root / "sandbox"
        self.artifacts.mkdir()
        self.sandbox.mkdir()
        self.source = self.artifacts / self.source_name
        self.source.write_text("offline fixture package artifact", encoding="utf-8")
        self.target = self.sandbox / "install-target"
        self.current_state = PackageInstallCurrentState(
            current_tick=15,
            dependency_context_hash="a" * 64,
            target_environment_hash="b" * 64,
            sandbox_root=str(self.sandbox),
            offline_artifact_root=str(self.artifacts),
            offline_mode=True,
            network_disabled=True,
            package_registry_access_disabled=True,
        )
        self.proposal_request = PackageInstallProposalRequest(
            ecosystem=self.ecosystem,
            package_name=self.package_name,
            version=self.version,
            reason="Review controlled offline sandbox package install only.",
            requested_by="local-human-operator",
            created_at_tick=10,
            expires_at_tick=20,
            toctou_evidence={
                "dependency_context_hash": self.current_state.dependency_context_hash,
                "target_environment_hash": self.current_state.target_environment_hash,
                "observed_at_tick": 10,
            },
            proposal_id="step43-package-install",
            source_id="local-fixture",
            source_hash="c" * 64,
            metadata={"scope": "offline-sandbox"},
        )
        self.validation_result = propose_package_install(self.proposal_request, now_tick=15)
        self.barrier = create_package_install_human_barrier(
            proposal_hash=compute_package_install_request_hash(self.proposal_request),
            validation_hash=self.validation_result.proposal_hash,
            ecosystem=self.validation_result.ecosystem,
            package_name=self.validation_result.package_name,
            package_version=self.validation_result.version,
            source=str(self.source),
            target=str(self.target),
            dependency_context_hash=self.current_state.dependency_context_hash,
            target_environment_hash=self.current_state.target_environment_hash,
            approved_by="local-human-operator",
            approval_reason="Approve offline temporary sandbox package install only.",
            approved_at=10,
            expires_at=20,
        )
        return self

    def __exit__(self, exc_type, exc, tb):
        self.temp.cleanup()
        return False


class FakeRunner:
    def __init__(self, *, exit_code: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.calls: list[dict] = []

    def run(self, argv, *, cwd, env, timeout_seconds):
        self.calls.append(
            {
                "argv": tuple(argv),
                "cwd": Path(cwd),
                "env": dict(env),
                "timeout_seconds": timeout_seconds,
            }
        )
        return type(
            "RunnerResult",
            (),
            {
                "exit_code": self.exit_code,
                "stdout": self.stdout,
                "stderr": self.stderr,
                "timeout_expired": False,
            },
        )()


class FakeVenvBuilder:
    def create(self, target_path: Path) -> None:
        bin_dir = target_path / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        (bin_dir / "python").write_text("# fake python\n", encoding="utf-8")


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
