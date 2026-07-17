from __future__ import annotations

import ast
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from tests import static_capability_boundary_support_1a as step14


REPO_ROOT = Path(__file__).resolve().parents[1]

CORE_NO_AUTHORITY_MODULES = (
    "runtime/artifact_preview.py",
    "runtime/providers/critic.py",
    "runtime/providers/critic_taxonomy.py",
    "runtime/providers/critic_adversarial_corpus.py",
    "runtime/providers/provider_controlled_expansion.py",
    "runtime/providers/provider_gateway_guard.py",
    "runtime/providers/provider_payload_governance.py",
    "runtime/providers/provider_response_schema.py",
    "runtime/package_ops/package_install_proposal.py",
    "runtime/schemas/action_proposal.py",
    "runtime/audit/durable_log.py",
)

ADDITIONAL_METADATA_REVIEW_MODULES = (
    "runtime/schemas/tool_call_preview.py",
    "runtime/schemas/tool_registry.py",
    "runtime/schemas/intent_router.py",
    "runtime/schemas/local_policy_engine.py",
    "runtime/schemas/test_runner_controller.py",
    "runtime/schemas/download_manager_governance.py",
    "runtime/schemas/statement_manager_governance.py",
    "runtime/schemas/browser_governance.py",
    "runtime/browser_ops/browser_automation_preview.py",
    "runtime/browser_ops/browser_automation_governance.py",
    "runtime/browser_ops/controlled_browser_automation.py",
    "runtime/integration_boundaries/coding_assistant_boundary.py",
    "runtime/integration_boundaries/mcp_boundary.py",
    "runtime/orchestration/async_io_orchestration.py",
    "runtime/orchestration/feedback_recovery_loop.py",
    "runtime/live_flows/codex_live_flow.py",
    "runtime/agent_loops/local_agent_loop.py",
    "runtime/agent_loops/provider_agent_loop.py",
    "runtime/memory/runtime_schemas.py",
    "runtime/provider_request_review.py",
    "runtime/provider_config_review.py",
    "runtime/provider_live_readiness_review.py",
    "runtime/git_ops/git_checkpoint.py",
    "runtime/git_ops/git_write_preview.py",
    "runtime/git_ops/git_commit_preview.py",
    "runtime/git_ops/git_commit_barrier.py",
    "runtime/git_ops/git_push_preview.py",
    "runtime/git_ops/git_push_barrier.py",
    "runtime/secret_boundary_review.py",
    "runtime/human_review_decision.py",
    "runtime/human_review_decision_validator.py",
    "runtime/human_review_decision_projection.py",
    "runtime/decision_implication_review.py",
    "runtime/decision_review_handoff.py",
    "runtime/review_session_snapshot.py",
    "runtime/review_session_bundle.py",
    "runtime/review_packet_projection.py",
    "runtime/proposal_review_packet.py",
)

NO_AUTHORITY_MODULES = tuple(
    REPO_ROOT / item
    for item in (*CORE_NO_AUTHORITY_MODULES, *ADDITIONAL_METADATA_REVIEW_MODULES)
)

PROVIDER_GATEWAY = REPO_ROOT / "runtime/providers/gateway.py"
POST_PATCH_CONTROLLED_TEST_INTEGRATION = REPO_ROOT / "runtime/patches/post_patch_controlled_test_integration.py"
GIT_READ_ADAPTER = REPO_ROOT / "runtime/git_ops/git_read.py"
GIT_READ_GOVERNANCE = REPO_ROOT / "runtime/git_ops/git_governance.py"
GIT_STATE_CHECKPOINT = REPO_ROOT / "runtime/git_ops/git_checkpoint.py"
GIT_WRITE_PREVIEW = REPO_ROOT / "runtime/git_ops/git_write_preview.py"
GIT_COMMIT_PREVIEW = REPO_ROOT / "runtime/git_ops/git_commit_preview.py"
GIT_COMMIT_BARRIER = REPO_ROOT / "runtime/git_ops/git_commit_barrier.py"
GIT_PUSH_PREVIEW = REPO_ROOT / "runtime/git_ops/git_push_preview.py"
GIT_PUSH_BARRIER = REPO_ROOT / "runtime/git_ops/git_push_barrier.py"
CONTROLLED_GIT_COMMIT = REPO_ROOT / "runtime/git_ops/controlled_git_commit.py"
CONTROLLED_GIT_PUSH = REPO_ROOT / "runtime/git_ops/git_controlled_push.py"

PATCH_METADATA_BOUNDARY_MODULES = tuple(
    REPO_ROOT / item
    for item in (
        "runtime/patches/patch_preview.py",
        "runtime/patches/patch_policy.py",
        "runtime/patches/patch_barrier.py",
        "runtime/patches/controlled_patch_apply.py",
        "runtime/patches/post_patch_verification_plan.py",
    )
)

FORBIDDEN_IMPORT_PREFIXES = (
    "subprocess",
    "pty",
    "shlex",
    "socket",
    "ssl",
    "http.client",
    "urllib",
    "urllib.request",
    "requests",
    "httpx",
    "aiohttp",
    "webbrowser",
    "selenium",
    "playwright",
    "git",
    "GitPython",
    "openai",
    "anthropic",
    "google.generativeai",
    "google.genai",
    "ollama",
    "pip",
    "venv",
    "importlib",
    "runtime.control_write",
    "runtime.human_decision_gated_artifact_write",
    "runtime.safety.sandbox_artifact_runner",
    "runtime.providers.gateway",
    "runtime.provider_live_adapter",
    "runtime.execution",
    "runtime.webapp",
)

FORBIDDEN_CALLS = (
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
    "importlib.import_module",
    "import_module",
)

NETWORK_ENV_IMPORT_PREFIXES = (
    "os",
    "urllib",
    "urllib.request",
    "socket",
    "ssl",
    "http.client",
    "requests",
    "httpx",
    "aiohttp",
)

PROVIDER_SDK_IMPORT_PREFIXES = (
    "openai",
    "anthropic",
    "google.generativeai",
    "google.genai",
    "ollama",
)


@dataclass(frozen=True)
class StaticModuleScan:
    path: Path
    imports: tuple[str, ...]
    calls: tuple[str, ...]


class StaticCapabilityBoundary1ATests(unittest.TestCase):
    def test_static_scan_detects_forbidden_imports_in_metadata_review_modules(self):
        for path in NO_AUTHORITY_MODULES:
            with self.subTest(path=self.relative(path)):
                scan = scan_module(path)

                forbidden = [
                    module_name
                    for module_name in scan.imports
                    if matches_any_prefix(module_name, FORBIDDEN_IMPORT_PREFIXES)
                ]

                self.assertEqual([], forbidden)

    def test_static_scan_detects_forbidden_calls_in_metadata_review_modules(self):
        for path in NO_AUTHORITY_MODULES:
            with self.subTest(path=self.relative(path)):
                scan = scan_module(path)

                forbidden = [
                    call_name
                    for call_name in scan.calls
                    if call_name in FORBIDDEN_CALLS
                ]

                self.assertEqual([], forbidden)

    def test_core_metadata_modules_remain_no_authority(self):
        for relative in CORE_NO_AUTHORITY_MODULES:
            path = REPO_ROOT / relative
            with self.subTest(path=relative):
                scan = scan_module(path)

                forbidden = [
                    module_name
                    for module_name in scan.imports
                    if matches_any_prefix(
                        module_name,
                        (
                            "runtime.control_write",
                            "runtime.human_decision_gated_artifact_write",
                            "runtime.safety.sandbox_artifact_runner",
                            "runtime.providers.gateway",
                            "runtime.provider_live_adapter",
                            "runtime.execution",
                            "runtime.webapp",
                        ),
                    )
                ]

                self.assertEqual([], forbidden)

    def test_artifact_preview_boundary_enforced(self):
        self.assert_no_authority_surface("runtime/artifact_preview.py")

    def test_critic_boundary_enforced(self):
        self.assert_no_authority_surface("runtime/providers/critic.py")

    def test_action_proposal_boundary_enforced(self):
        self.assert_no_authority_surface("runtime/schemas/action_proposal.py")

    def test_durable_ledger_boundary_enforced(self):
        self.assert_no_authority_surface("runtime/audit/durable_log.py")

    def test_gateway_network_environment_surface_remains_isolated(self):
        self.assertTrue(PROVIDER_GATEWAY.exists())
        gateway_imports = scan_module(PROVIDER_GATEWAY).imports
        self.assertTrue(any(matches_any_prefix(item, NETWORK_ENV_IMPORT_PREFIXES) for item in gateway_imports))

        for path in NO_AUTHORITY_MODULES:
            with self.subTest(path=self.relative(path)):
                imports = scan_module(path).imports
                self.assertEqual(
                    [],
                    [
                        module_name
                        for module_name in imports
                        if matches_any_prefix(module_name, NETWORK_ENV_IMPORT_PREFIXES)
                    ],
                )

    def test_gateway_exception_does_not_allow_provider_sdk_imports_in_no_authority_modules(self):
        for path in (*NO_AUTHORITY_MODULES, PROVIDER_GATEWAY):
            with self.subTest(path=self.relative(path)):
                imports = scan_module(path).imports
                self.assertEqual(
                    [],
                    [
                        module_name
                        for module_name in imports
                        if matches_any_prefix(module_name, PROVIDER_SDK_IMPORT_PREFIXES)
                    ],
                )

    def test_dynamic_import_is_blocked_in_metadata_review_modules(self):
        dynamic_import_calls = {"__import__", "importlib.import_module", "import_module"}

        for path in NO_AUTHORITY_MODULES:
            with self.subTest(path=self.relative(path)):
                scan = scan_module(path)

                self.assertEqual(
                    [],
                    [call_name for call_name in scan.calls if call_name in dynamic_import_calls],
                )

    def test_write_gate_bypass_imports_are_blocked_in_metadata_review_modules(self):
        bypass_prefixes = (
            "runtime.control_write",
            "runtime.human_decision_gated_artifact_write",
            "runtime.safety.sandbox_artifact_runner",
            "runtime.safety.approval",
            "runtime.safety.gated",
            "runtime.execution",
            "runtime.webapp",
            "runtime.providers.gateway",
            "runtime.provider_live_adapter",
        )

        for path in NO_AUTHORITY_MODULES:
            with self.subTest(path=self.relative(path)):
                scan = scan_module(path)

                self.assertEqual(
                    [],
                    [
                        module_name
                        for module_name in scan.imports
                        if matches_any_prefix(module_name, bypass_prefixes)
                    ],
                )

    def test_post_patch_and_git_read_subprocess_exceptions_are_narrow(self):
        self.assertTrue(POST_PATCH_CONTROLLED_TEST_INTEGRATION.exists())
        step_26_scan = scan_module(POST_PATCH_CONTROLLED_TEST_INTEGRATION)
        self.assertIn("subprocess", step_26_scan.imports)
        self.assertIn("subprocess.run", step_26_scan.calls)
        self.assertNotIn("subprocess.Popen", step_26_scan.calls)
        source = POST_PATCH_CONTROLLED_TEST_INTEGRATION.read_text(encoding="utf-8").casefold()
        self.assertNotIn("shell=true", source)

        self.assertTrue(GIT_READ_ADAPTER.exists())
        git_scan = scan_module(GIT_READ_ADAPTER)
        self.assertIn("subprocess", git_scan.imports)
        self.assertIn("subprocess.run", git_scan.calls)
        self.assertNotIn("subprocess.Popen", git_scan.calls)
        git_source = GIT_READ_ADAPTER.read_text(encoding="utf-8").casefold()
        self.assertNotIn("shell=true", git_source)
        self.assertNotIn("os.environ", git_source)
        self.assertNotIn("getenv", git_source)

        self.assertTrue(GIT_READ_GOVERNANCE.exists())
        governance_scan = scan_module(GIT_READ_GOVERNANCE)
        self.assertNotIn("subprocess", governance_scan.imports)
        self.assertNotIn("subprocess.run", governance_scan.calls)
        self.assertNotIn("subprocess.Popen", governance_scan.calls)
        governance_source = GIT_READ_GOVERNANCE.read_text(encoding="utf-8").casefold()
        self.assertNotIn("shell=true", governance_source)
        self.assertNotIn("os.environ", governance_source)
        self.assertNotIn("getenv", governance_source)

        self.assertTrue(GIT_STATE_CHECKPOINT.exists())
        checkpoint_scan = scan_module(GIT_STATE_CHECKPOINT)
        self.assertNotIn("subprocess", checkpoint_scan.imports)
        self.assertNotIn("subprocess.run", checkpoint_scan.calls)
        self.assertNotIn("subprocess.Popen", checkpoint_scan.calls)
        checkpoint_source = GIT_STATE_CHECKPOINT.read_text(encoding="utf-8").casefold()
        self.assertNotIn("shell=true", checkpoint_source)
        self.assertNotIn("os.environ", checkpoint_source)
        self.assertNotIn("getenv", checkpoint_source)

        self.assertTrue(GIT_WRITE_PREVIEW.exists())
        write_preview_scan = scan_module(GIT_WRITE_PREVIEW)
        self.assertNotIn("subprocess", write_preview_scan.imports)
        self.assertNotIn("subprocess.run", write_preview_scan.calls)
        self.assertNotIn("subprocess.Popen", write_preview_scan.calls)
        write_preview_source = GIT_WRITE_PREVIEW.read_text(encoding="utf-8").casefold()
        self.assertNotIn("shell=true", write_preview_source)
        self.assertNotIn("os.environ", write_preview_source)
        self.assertNotIn("getenv", write_preview_source)

        self.assertTrue(GIT_COMMIT_PREVIEW.exists())
        commit_preview_scan = scan_module(GIT_COMMIT_PREVIEW)
        self.assertNotIn("subprocess", commit_preview_scan.imports)
        self.assertNotIn("subprocess.run", commit_preview_scan.calls)
        self.assertNotIn("subprocess.Popen", commit_preview_scan.calls)
        commit_preview_source = GIT_COMMIT_PREVIEW.read_text(encoding="utf-8").casefold()
        self.assertNotIn("shell=true", commit_preview_source)
        self.assertNotIn("os.environ", commit_preview_source)
        self.assertNotIn("getenv", commit_preview_source)

        self.assertTrue(GIT_PUSH_PREVIEW.exists())
        push_preview_scan = scan_module(GIT_PUSH_PREVIEW)
        self.assertNotIn("subprocess", push_preview_scan.imports)
        self.assertNotIn("subprocess.run", push_preview_scan.calls)
        self.assertNotIn("subprocess.Popen", push_preview_scan.calls)
        push_preview_source = GIT_PUSH_PREVIEW.read_text(encoding="utf-8").casefold()
        self.assertNotIn("shell=true", push_preview_source)
        self.assertNotIn("os.environ", push_preview_source)
        self.assertNotIn("getenv", push_preview_source)

        self.assertTrue(GIT_PUSH_BARRIER.exists())
        push_barrier_scan = scan_module(GIT_PUSH_BARRIER)
        self.assertNotIn("subprocess", push_barrier_scan.imports)
        self.assertNotIn("subprocess.run", push_barrier_scan.calls)
        self.assertNotIn("subprocess.Popen", push_barrier_scan.calls)
        push_barrier_source = GIT_PUSH_BARRIER.read_text(encoding="utf-8").casefold()
        self.assertNotIn("shell=true", push_barrier_source)
        self.assertNotIn("os.environ", push_barrier_source)
        self.assertNotIn("getenv", push_barrier_source)

        self.assertTrue(CONTROLLED_GIT_COMMIT.exists())
        controlled_commit_scan = scan_module(CONTROLLED_GIT_COMMIT)
        self.assertIn("subprocess", controlled_commit_scan.imports)
        self.assertIn("subprocess.run", controlled_commit_scan.calls)
        self.assertNotIn("subprocess.Popen", controlled_commit_scan.calls)
        controlled_commit_source = CONTROLLED_GIT_COMMIT.read_text(encoding="utf-8").casefold()
        for forbidden in (
            "shell=true",
            "os.environ",
            "getenv",
            "api.github.com",
            "git push",
            "ls-remote",
            "requests",
            "httpx",
            "webbrowser",
            "selenium",
            "playwright",
            "openai",
            "anthropic",
        ):
            self.assertNotIn(forbidden, controlled_commit_source)

        self.assertTrue(CONTROLLED_GIT_PUSH.exists())
        controlled_push_scan = scan_module(CONTROLLED_GIT_PUSH)
        self.assertIn("subprocess", controlled_push_scan.imports)
        self.assertIn("subprocess.run", controlled_push_scan.calls)
        self.assertNotIn("subprocess.Popen", controlled_push_scan.calls)
        controlled_push_source = CONTROLLED_GIT_PUSH.read_text(encoding="utf-8").casefold()
        for forbidden in (
            "shell=true",
            "os.environ",
            "getenv",
            "api.github.com",
            "requests",
            "httpx",
            "webbrowser",
            "selenium",
            "playwright",
            "openai",
            "anthropic",
        ):
            self.assertNotIn(forbidden, controlled_push_source)

        forbidden_patch_imports = (
            "subprocess",
            "socket",
            "urllib",
            "requests",
            "httpx",
            "webbrowser",
            "selenium",
            "playwright",
            "git",
            "openai",
            "anthropic",
            "runtime.providers.gateway",
            "runtime.execution",
        )
        forbidden_patch_calls = (
            "subprocess.run",
            "subprocess.Popen",
            "subprocess.call",
            "subprocess.check_call",
            "subprocess.check_output",
            "os.system",
            "Popen",
        )
        for path in PATCH_METADATA_BOUNDARY_MODULES:
            with self.subTest(path=self.relative(path)):
                scan = scan_module(path)
                self.assertEqual(
                    [],
                    [
                        module_name
                        for module_name in scan.imports
                        if matches_any_prefix(module_name, forbidden_patch_imports)
                    ],
                )
                self.assertEqual([], [call_name for call_name in scan.calls if call_name in forbidden_patch_calls])

    def assert_no_authority_surface(self, relative_path: str) -> None:
        scan = scan_module(REPO_ROOT / relative_path)
        self.assertEqual(
            [],
            [
                module_name
                for module_name in scan.imports
                if matches_any_prefix(module_name, FORBIDDEN_IMPORT_PREFIXES)
            ],
        )
        self.assertEqual(
            [],
            [call_name for call_name in scan.calls if call_name in FORBIDDEN_CALLS],
        )

    @staticmethod
    def relative(path: Path) -> str:
        return path.relative_to(REPO_ROOT).as_posix()


class StaticCapabilityScannerStep14Tests(unittest.TestCase):
    def scan(self, source: str, zone: str = "other_inert"):
        return step14.scan_source_for_capabilities(
            source,
            path="runtime/synthetic_step14_fixture.py",
            zone_name=zone,
        )

    def test_step14_detects_direct_forbidden_imports(self):
        fixtures = {
            "subprocess": "import subprocess",
            "subprocess-alias": "import subprocess as sp",
            "subprocess-from": "from subprocess import Popen",
            "socket": "import socket",
            "requests": "import requests",
            "webbrowser": "import webbrowser",
            "selenium": "import selenium",
            "playwright": "import playwright",
            "git": "import git",
            "openai": "import openai",
            "anthropic": "import anthropic",
            "pip": "import pip",
        }

        for name, source in fixtures.items():
            with self.subTest(name=name):
                self.assertTrue(self.scan(source))

    def test_step14_detects_aliased_dangerous_calls(self):
        fixtures = {
            "subprocess-module-alias": "import subprocess as sp\nsp.run(['safe-test-data'])",
            "subprocess-symbol-alias": "from subprocess import run as execute\nexecute(['safe-test-data'])",
            "popen-symbol-alias": "from subprocess import Popen as launch\nlaunch(['safe-test-data'])",
            "os-system": "import os\nos.system('inert')",
            "os-module-alias": "import os as operating_system\noperating_system.system('inert')",
            "os-symbol-alias": "from os import system as execute\nexecute('inert')",
            "browser-alias": "import webbrowser as browser\nbrowser.open('https://invalid.example')",
        }

        for name, source in fixtures.items():
            with self.subTest(name=name):
                findings = self.scan(source)
                self.assertTrue(findings)
                self.assertTrue(
                    any(
                        finding.category in {
                            "dangerous-call",
                            "dangerous-symbol-import",
                        }
                        for finding in findings
                    )
                )

    def test_step14_detects_literal_and_unresolved_dynamic_imports(self):
        fixtures = {
            "literal-importlib": (
                "import importlib as loader\n"
                "loader.import_module('subprocess')"
            ),
            "literal-builtins": "__import__('socket')",
            "from-import-alias": (
                "from importlib import import_module as load\n"
                "load('requests')"
            ),
            "unresolved": (
                "import importlib as loader\n"
                "module_name = 'pathlib'\n"
                "loader.import_module(module_name)"
            ),
        }

        for name, source in fixtures.items():
            with self.subTest(name=name):
                findings = self.scan(source)
                self.assertIn(
                    "dynamic-import",
                    {finding.category for finding in findings},
                )

    def test_step14_detects_shell_true_on_any_call(self):
        findings = self.scan("runner(['inert'], shell=True)")
        self.assertIn("shell-true", {finding.category for finding in findings})

    def test_step14_detects_routing_dispatch_and_filesystem_writes(self):
        fixtures = {
            "injected-retrieval": "def route(self, query):\n    return self.retrieve(query)",
            "callable-candidate": "def route(route_candidate):\n    return route_candidate()",
            "generic-dispatch": "def route(dispatch):\n    return dispatch()",
            "path-write-text": (
                "from pathlib import Path\n"
                "Path('token_savings_report.json').write_text('data')"
            ),
            "path-write-bytes": (
                "from pathlib import Path\n"
                "Path('token_savings_report.json').write_bytes(b'data')"
            ),
            "open-write": "open('token_savings_report.json', 'w')",
            "open-append": "open('token_savings_report.json', mode='a')",
        }

        for name, source in fixtures.items():
            with self.subTest(name=name):
                findings = self.scan(source, zone="knowledge_routing")
                self.assertTrue(findings)
                self.assertTrue(
                    {finding.category for finding in findings}.intersection(
                        {"routing-dispatch", "routing-filesystem-write"}
                    )
                )

    def test_step14_routing_scan_ignores_inert_execution_looking_strings(self):
        source = '''
examples = (
    "self.retrieve(query)",
    "Path.write_text",
    "token_savings_report.json",
)
# open("report.json", "w")
'''
        self.assertEqual((), self.scan(source, zone="knowledge_routing"))

    def test_step14_detects_direct_authority_boundary_import(self):
        fixtures = {
            "human-writer": (
                "from runtime.human_decision_gated_artifact_write "
                "import write_artifact_after_human_gate"
            ),
            "control-write": "from runtime.control_write import write_preview_artifact_after_human_gate",
            "sandbox-writer": "from runtime.safety.sandbox_artifact_runner import write_sandbox_artifact",
            "provider-gateway": "from runtime.providers.gateway import ProviderGateway",
            "patch-apply": "from runtime.patches.controlled_patch_apply import apply_patch",
            "git-write": "from runtime.git_ops.controlled_git_commit import controlled_git_commit",
            "package-install": "from runtime.package_ops.controlled_package_install import install_package",
            "browser": "from runtime.browser_ops.controlled_browser_automation import run_browser_automation",
            "executor": "from runtime.tools.executor import execute_tool",
        }
        for name, source in fixtures.items():
            with self.subTest(name=name):
                findings = self.scan(source)
                self.assertIn(
                    "authority-boundary-import",
                    {finding.category for finding in findings},
                )

    def test_step14_strict_policy_blocks_workspace_gate_and_agent_helpers(self):
        fixtures = {
            "workspace": "from runtime.safety.workspace_guard import WorkspaceGuard",
            "approval": "from runtime.human_approval_gate import evaluate_human_approval_gate",
            "agent": "from runtime.agent_loops.local_agent_loop import run_local_agent_loop",
            "orchestration": "from runtime.orchestration.async_io_orchestration import orchestrate",
        }
        for name, source in fixtures.items():
            with self.subTest(name=name):
                findings = step14.scan_source_for_capabilities(
                    source,
                    path=f"runtime/{name}.py",
                    zone_name="action_proposal",
                    enforce_inert_side_effects=True,
                )
                self.assertIn(
                    "authority-boundary-import",
                    {finding.category for finding in findings},
                )

    def test_step14_ignores_comments_and_inert_strings(self):
        source = """
# import subprocess
command = "sudo apt install curl"
example = "import requests"
gate_data = {"approved": True, "entry_hash": "metadata-only"}
"""
        self.assertEqual((), self.scan(source))

    def test_step14_allows_inert_standard_library_operations(self):
        fixtures = {
            "url-parsing": "from urllib import parse\nparse.urlsplit('https://example.invalid')",
            "audit-fsync": "import os\nos.fsync(1)",
            "audit-flock": "import fcntl\nfcntl.flock(1, fcntl.LOCK_EX)",
            "pathlib": "from pathlib import Path\nvalue = Path('inert')",
            "hashlib": "import hashlib\nvalue = hashlib.sha256(b'inert').hexdigest()",
            "dataclass": "from dataclasses import dataclass\n@dataclass(frozen=True)\nclass Record:\n    value: str",
            "annotations": "from typing import Mapping\nvalue: Mapping[str, object]",
            "canonical-json": "import json\njson.dumps({'b': 2, 'a': 1}, sort_keys=True)",
            "safe-literal-dynamic-import": (
                "import importlib\nimportlib.import_module('pathlib')"
            ),
        }

        for name, source in fixtures.items():
            with self.subTest(name=name):
                self.assertEqual((), self.scan(source, zone="audit"))

    def test_step14_detects_imports_inside_functions_conditions_and_type_checking(self):
        fixtures = {
            "function": "def hidden():\n    import requests",
            "conditional": "if False:\n    import subprocess",
            "type-checking": (
                "from typing import TYPE_CHECKING\n"
                "if TYPE_CHECKING:\n"
                "    import openai"
            ),
        }

        for name, source in fixtures.items():
            with self.subTest(name=name):
                self.assertTrue(self.scan(source))

    def test_step14_syntax_errors_fail_closed(self):
        findings = self.scan("def broken(:\n    pass")
        self.assertEqual(1, len(findings))
        self.assertEqual("syntax-error", findings[0].category)

    def test_step14_invalid_utf8_fails_closed(self):
        with tempfile.TemporaryDirectory() as root_name:
            root = Path(root_name)
            (root / "invalid.py").write_bytes(b"\xff\xfe")
            findings = step14.scan_file_for_capabilities(
                root,
                step14.ProtectedRuntimeFile(
                    path="invalid.py",
                    zone="other_inert",
                ),
            )
        self.assertEqual(1, len(findings))
        self.assertEqual("invalid-utf8", findings[0].category)

    def test_step14_findings_are_immutable_and_deterministically_sorted(self):
        findings = self.scan("import socket\nimport subprocess\n")
        self.assertEqual(tuple(sorted(findings)), findings)
        self.assertEqual(
            ["network-import", "process-import"],
            [finding.category for finding in findings],
        )
        with self.assertRaises(AttributeError):
            findings[0].line = 99

    def test_step14_unknown_zone_fails_closed(self):
        with self.assertRaises(step14.StaticCapabilityPolicyError):
            step14.scan_source_for_capabilities(
                "import pathlib",
                path="runtime/synthetic.py",
                zone_name="unknown-zone",
            )

    def test_step14_outside_and_symlink_escape_paths_fail_closed(self):
        with self.assertRaises(step14.StaticCapabilityPolicyError):
            step14.scan_file_for_capabilities(
                REPO_ROOT,
                step14.ProtectedRuntimeFile(
                    path="/etc/hosts",
                    zone="other_inert",
                ),
            )

        with tempfile.TemporaryDirectory() as root_name:
            root = Path(root_name)
            escape = root / "escape.py"
            escape.symlink_to(Path(__file__).resolve())
            with self.assertRaises(step14.StaticCapabilityPolicyError):
                step14.scan_file_for_capabilities(
                    root,
                    step14.ProtectedRuntimeFile(
                        path="escape.py",
                        zone="other_inert",
                    ),
                )


class StaticCapabilityImportGraphStep14Tests(unittest.TestCase):
    @staticmethod
    def write_fixture(root: Path, relative: str, source: str) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
        return path

    @staticmethod
    def graph_findings(reports):
        return tuple(
            finding
            for report in reports
            for finding in report.violations
        )

    def test_step14_strict_scan_blocks_write_and_environment_capabilities(self):
        fixtures = {
            "open-write": "open('artifact.txt', 'w')",
            "builtins-open-alias": (
                "from builtins import open as mutate\n"
                "mutate('artifact.txt', mode='a')"
            ),
            "path-write": (
                "from pathlib import Path as P\n"
                "P('artifact.txt').write_text('data')"
            ),
            "assigned-path-write": (
                "from pathlib import Path\n"
                "path = Path('artifact.txt')\n"
                "path.write_bytes(b'data')"
            ),
            "path-replace": (
                "from pathlib import Path\n"
                "Path('source').replace(Path('target'))"
            ),
            "os-open": (
                "import os as operating_system\n"
                "operating_system.open('artifact.txt', operating_system.O_CREAT)"
            ),
            "os-remove": "from os import remove as erase\nerase('artifact.txt')",
            "shutil-copy": "import shutil as files\nfiles.copy('a', 'b')",
            "tempfile": "import tempfile\ntempfile.NamedTemporaryFile()",
            "getenv": "from os import getenv as secret\nsecret('OPENAI_API_KEY')",
            "environ": "import os\nvalue = os.environ['OPENAI_API_KEY']",
            "dotenv": "import dotenv",
            "keyring": "import keyring",
        }

        for name, source in fixtures.items():
            with self.subTest(name=name):
                findings = step14.scan_source_for_capabilities(
                    source,
                    path=f"runtime/{name}.py",
                    zone_name="provider_critic",
                    enforce_inert_side_effects=True,
                )
                self.assertTrue(findings)
                self.assertTrue(
                    {finding.category for finding in findings}.intersection(
                        {
                            "environment-access",
                            "filesystem-mutation",
                            "secret-import",
                        }
                    )
                )

    def test_step14_audit_filesystem_exception_is_exact_and_operation_specific(self):
        destructive_sources = {
            "os-unlink": "import os\nos.unlink('evidence.jsonl')\n",
            "shutil-rmtree": "import shutil\nshutil.rmtree('records')\n",
            "path-write-text": (
                "from pathlib import Path\n"
                "Path('record.jsonl').write_text('forged')\n"
            ),
            "os-open-truncate": (
                "import os\n"
                "os.open('record.jsonl', os.O_WRONLY | os.O_TRUNC)\n"
            ),
        }
        non_ledger_paths = (
            "runtime/audit/other.py",
            "runtime/audit/durable_audit_ledger_extra.py",
            "runtime/audit/durable_log.py",
            "runtime/audit_ledger.py",
            "nested/runtime/audit/durable_audit_ledger.py",
            "../runtime/audit/durable_audit_ledger.py",
            "/outside/runtime/audit/durable_audit_ledger.py",
        )

        for path in non_ledger_paths:
            for name, source in destructive_sources.items():
                with self.subTest(path=path, operation=name):
                    findings = step14.scan_source_for_capabilities(
                        source,
                        path=path,
                        zone_name="audit",
                        enforce_inert_side_effects=True,
                    )
                    self.assertIn(
                        "filesystem-mutation",
                        {finding.category for finding in findings},
                    )

        ledger_path = "runtime/audit/durable_audit_ledger.py"
        for name, source in destructive_sources.items():
            with self.subTest(path=ledger_path, operation=name):
                findings = step14.scan_source_for_capabilities(
                    source,
                    path=ledger_path,
                    zone_name="audit",
                    enforce_inert_side_effects=True,
                )
                self.assertIn(
                    "filesystem-mutation",
                    {finding.category for finding in findings},
                )

        policy_shaped_sources = {
            "environment": (
                "import os\n"
                "configured = os.environ.get('AOIA_LEDGER_EXCEPTION')\n"
                "os.unlink('evidence.jsonl')\n"
            ),
            "metadata": (
                "import os\n"
                "provider_metadata = {'allow_filesystem': True, "
                "'path': 'runtime/audit/durable_audit_ledger.py'}\n"
                "os.unlink('evidence.jsonl')\n"
            ),
        }
        for name, source in policy_shaped_sources.items():
            with self.subTest(policy_input=name):
                findings = step14.scan_source_for_capabilities(
                    source,
                    path=ledger_path,
                    zone_name="audit",
                    enforce_inert_side_effects=True,
                )
                self.assertIn(
                    "filesystem-mutation",
                    {finding.category for finding in findings},
                )

        gateway_findings = step14.scan_source_for_capabilities(
            "import os\nos.unlink('ledger.jsonl')\n",
            path="runtime/providers/gateway.py",
            zone_name="provider_critic",
            enforce_inert_side_effects=True,
        )
        self.assertIn(
            "filesystem-mutation",
            {finding.category for finding in gateway_findings},
        )

        safe_read = step14.scan_source_for_capabilities(
            "from pathlib import Path\nPath('record.jsonl').read_bytes()\n",
            path="runtime/audit/other.py",
            zone_name="audit",
            enforce_inert_side_effects=True,
        )
        self.assertEqual((), safe_read)

        allowed_append = step14.scan_source_for_capabilities(
            (
                "import os\n"
                "os.open('record.jsonl', "
                "os.O_RDWR | os.O_APPEND | os.O_CREAT, 0o600)\n"
            ),
            path=ledger_path,
            zone_name="audit",
            enforce_inert_side_effects=True,
        )
        self.assertEqual((), allowed_append)

    def test_step14_ledger_exception_does_not_propagate_to_helpers(self):
        import_forms = {
            "relative": "from .helper import value\n",
            "absolute": "from runtime.audit.helper import value\n",
            "package-reexport": "from runtime.audit import value\n",
        }
        for name, ledger_import in import_forms.items():
            with self.subTest(import_form=name):
                with tempfile.TemporaryDirectory() as root_name:
                    root = Path(root_name)
                    self.write_fixture(root, "runtime/__init__.py", "")
                    self.write_fixture(
                        root,
                        "runtime/audit/__init__.py",
                        (
                            "from .helper import value\n"
                            if name == "package-reexport"
                            else ""
                        ),
                    )
                    self.write_fixture(
                        root,
                        "runtime/audit/durable_audit_ledger.py",
                        ledger_import,
                    )
                    self.write_fixture(
                        root,
                        "runtime/audit/helper.py",
                        (
                            "from pathlib import Path\n"
                            "Path('forged.jsonl').write_text('forged')\n"
                            "value = None\n"
                        ),
                    )
                    reports = step14.scan_step14_import_graph(
                        root,
                        (
                            step14.ProtectedRuntimeFile(
                                path="runtime/audit/durable_audit_ledger.py",
                                zone="audit",
                            ),
                        ),
                    )

                findings = self.graph_findings(reports)
                self.assertIn(
                    "filesystem-mutation",
                    {finding.category for finding in findings},
                )
                formatted = step14.format_violations(findings)
                self.assertIn("runtime/audit/durable_audit_ledger.py ->", formatted)
                self.assertIn("runtime/audit/helper.py", formatted)

    def test_step14_real_ledger_uses_only_exact_allowed_filesystem_operations(self):
        ledger_path = "runtime/audit/durable_audit_ledger.py"
        source = (REPO_ROOT / ledger_path).read_text(encoding="utf-8")
        findings = step14.scan_source_for_capabilities(
            source,
            path=ledger_path,
            zone_name="audit",
            enforce_inert_side_effects=True,
        )
        self.assertEqual((), findings)
        self.assertEqual(
            (
                "fcntl.flock",
                "os.close",
                "os.fdopen",
                "os.fsync",
                "os.open",
            ),
            step14.LEDGER_ALLOWED_FILESYSTEM_CALLS,
        )

        malicious_source = source + "\nimport os\nos.unlink('forged.jsonl')\n"
        malicious_findings = step14.scan_source_for_capabilities(
            malicious_source,
            path=ledger_path,
            zone_name="audit",
            enforce_inert_side_effects=True,
        )
        self.assertIn(
            "filesystem-mutation",
            {finding.category for finding in malicious_findings},
        )

    def test_step14_transitive_relative_reexport_and_gateway_bypasses_fail_closed(self):
        with tempfile.TemporaryDirectory() as root_name:
            root = Path(root_name)
            self.write_fixture(root, "runtime/__init__.py", "")
            self.write_fixture(
                root,
                "runtime/protected.py",
                (
                    "from .reexport import launch\n"
                    "from . import relative_writer\n"
                    "from importlib import import_module as load\n"
                    "dynamic_helper = load('runtime.dynamic_helper')\n"
                    "import runtime.reexport_package\n"
                ),
            )
            self.write_fixture(
                root,
                "runtime/reexport.py",
                "from runtime.helper import launch\n",
            )
            self.write_fixture(
                root,
                "runtime/helper.py",
                "import subprocess as process\nlaunch = process.run\n",
            )
            self.write_fixture(root, "runtime/dynamic_helper.py", "import socket\n")
            self.write_fixture(root, "runtime/reexport_package/__init__.py", "from runtime.helper import launch\n")
            self.write_fixture(
                root,
                "runtime/relative_writer.py",
                "from .control_write import write_preview_artifact_after_human_gate\n",
            )
            self.write_fixture(root, "runtime/control_write.py", "")

            reports = step14.scan_step14_import_graph(
                root,
                (
                    step14.ProtectedRuntimeFile(
                        path="runtime/protected.py",
                        zone="provider_critic",
                    ),
                ),
            )

        findings = self.graph_findings(reports)
        categories = {finding.category for finding in findings}
        self.assertIn("process-import", categories)
        self.assertIn("network-import", categories)
        self.assertIn("authority-boundary-import", categories)
        formatted = step14.format_violations(findings)
        self.assertIn(
            "runtime/protected.py -> runtime/reexport.py -> runtime/helper.py",
            formatted,
        )
        self.assertIn(
            "runtime/protected.py -> runtime/relative_writer.py -> runtime/control_write.py",
            formatted,
        )

    def test_step14_gateway_exception_is_non_transitive(self):
        with tempfile.TemporaryDirectory() as root_name:
            root = Path(root_name)
            self.write_fixture(root, "runtime/__init__.py", "")
            self.write_fixture(
                root,
                "runtime/protected.py",
                "from runtime.shared_helper import value\n",
            )
            self.write_fixture(root, "runtime/shared_helper.py", "import requests\nvalue = None\n")
            self.write_fixture(root, "runtime/providers/__init__.py", "")
            self.write_fixture(
                root,
                "runtime/providers/gateway.py",
                "from runtime.shared_helper import value\n",
            )

            reports = step14.scan_step14_import_graph(
                root,
                (
                    step14.ProtectedRuntimeFile(
                        path="runtime/protected.py",
                        zone="provider_critic",
                    ),
                ),
                gateway_exceptions=("runtime/providers/gateway.py",),
            )

        findings = self.graph_findings(reports)
        self.assertIn("network-import", {finding.category for finding in findings})
        self.assertTrue(all(not report.exemptions_applied for report in reports))

    def test_step14_missing_local_modules_fail_closed_and_cycles_terminate(self):
        with tempfile.TemporaryDirectory() as root_name:
            root = Path(root_name)
            self.write_fixture(root, "runtime/__init__.py", "")
            self.write_fixture(root, "runtime/protected.py", "from .cycle_a import value\n")
            self.write_fixture(root, "runtime/cycle_a.py", "from .cycle_b import value\n")
            self.write_fixture(root, "runtime/cycle_b.py", "from .cycle_a import value\nvalue = 1\n")

            clean_reports = step14.scan_step14_import_graph(
                root,
                (
                    step14.ProtectedRuntimeFile(
                        path="runtime/protected.py",
                        zone="provider_critic",
                    ),
                ),
            )
            self.assertEqual((), self.graph_findings(clean_reports))
            self.assertEqual(
                (
                    "runtime/cycle_a.py",
                    "runtime/cycle_b.py",
                    "runtime/protected.py",
                ),
                clean_reports[0].scanned_paths,
            )

            self.write_fixture(root, "runtime/cycle_b.py", "from .missing import value\n")
            missing_reports = step14.scan_step14_import_graph(
                root,
                (
                    step14.ProtectedRuntimeFile(
                        path="runtime/protected.py",
                        zone="provider_critic",
                    ),
                ),
            )

            with self.assertRaises(step14.StaticCapabilityPolicyError):
                step14.scan_step14_import_graph(
                    root,
                    (
                        step14.ProtectedRuntimeFile(
                            path="runtime/not_present.py",
                            zone="provider_critic",
                        ),
                    ),
                )

        findings = self.graph_findings(missing_reports)
        self.assertIn("unresolved-local-import", {item.category for item in findings})

    def test_step14_accepted_core_policy_is_explicit_complete_and_clean(self):
        records = step14.resolve_step14_core_protected_files(REPO_ROOT)
        paths = {record.path for record in records}
        self.assertEqual(set(step14.STEP14_CORE_PROTECTED_PATHS), paths)
        self.assertTrue(
            {
                "runtime/providers/critic.py",
                "runtime/artifact_preview.py",
                "runtime/schemas/action_proposal.py",
                "runtime/audit/durable_audit_ledger.py",
            }.issubset(paths)
        )

        reports = step14.scan_step14_import_graph(REPO_ROOT, records)
        self.assertEqual(paths, {report.root_path for report in reports})
        self.assertEqual((), self.graph_findings(reports))
        self.assertTrue(all(not report.unresolved_imports for report in reports))

    def test_step14_policy_result_is_non_authoritative_and_scanner_never_executes_sources(self):
        from runtime.human_decision_gate_integration import (
            validate_canonical_human_gate_authority,
        )

        with tempfile.TemporaryDirectory() as root_name:
            root = Path(root_name)
            self.write_fixture(root, "runtime/__init__.py", "")
            self.write_fixture(
                root,
                "runtime/protected.py",
                "from .inert_helper import value\n",
            )
            self.write_fixture(
                root,
                "runtime/inert_helper.py",
                "raise RuntimeError('scanner executed source')\nvalue = 1\n",
            )
            before = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*.py")
            }
            reports = step14.scan_step14_import_graph(
                root,
                (
                    step14.ProtectedRuntimeFile(
                        path="runtime/protected.py",
                        zone="provider_critic",
                    ),
                ),
            )
            after = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*.py")
            }

        self.assertEqual(before, after)
        self.assertEqual((), self.graph_findings(reports))
        scanner_scan = scan_module(
            REPO_ROOT / "tests/static_capability_boundary_support_1a.py"
        )
        self.assertTrue(
            set(scanner_scan.imports).issubset(
                {
                    "__future__",
                    "__future__.annotations",
                    "ast",
                    "dataclasses",
                    "dataclasses.dataclass",
                    "pathlib",
                    "pathlib.Path",
                    "typing",
                    "typing.Iterable",
                    "typing.Sequence",
                }
            )
        )
        self.assertEqual(
            [],
            [
                name
                for name in scanner_scan.calls
                if name in FORBIDDEN_CALLS
                or matches_any_prefix(name, FORBIDDEN_IMPORT_PREFIXES)
            ],
        )
        report = reports[0]
        self.assertFalse(hasattr(report, "approved"))
        self.assertFalse(hasattr(report, "allowed"))
        rejection = validate_canonical_human_gate_authority(
            report,
            expected_artifact_hash="a" * 64,
            expected_approval_decision_id="approval-step14",
            expected_audit_event_id="audit-step14",
            expected_contract_audit_event_id="audit-step14",
        )
        self.assertTrue(rejection)


class StaticCapabilityRepositoryStep14Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protected_files = step14.resolve_protected_runtime_files(REPO_ROOT)

    def test_step14_protected_zones_are_nonempty_unique_and_sorted(self):
        self.assertEqual(
            tuple(sorted(self.protected_files, key=lambda item: (item.path, item.zone))),
            self.protected_files,
        )
        paths = [record.path for record in self.protected_files]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertTrue(all((REPO_ROOT / path).is_file() for path in paths))

        for zone in step14.PROTECTED_ZONE_NAMES:
            with self.subTest(zone=zone):
                self.assertTrue(
                    [record for record in self.protected_files if record.zone == zone]
                )

    def test_step14_all_protected_repository_sources_are_clean(self):
        findings = step14.scan_protected_repository(REPO_ROOT)
        self.assertEqual("", step14.format_violations(findings))

    def test_step14_each_role_specific_zone_is_clean(self):
        for zone in step14.PROTECTED_ZONE_NAMES:
            with self.subTest(zone=zone):
                findings = step14.scan_protected_repository(REPO_ROOT, (zone,))
                self.assertEqual("", step14.format_violations(findings))

    def test_step14_audit_ledger_is_protected_and_local_durability_is_allowed(self):
        audit_paths = {
            record.path
            for record in self.protected_files
            if record.zone == "audit"
        }
        self.assertIn("runtime/audit/durable_audit_ledger.py", audit_paths)
        self.assertEqual(
            (),
            step14.scan_source_for_capabilities(
                "import fcntl\nimport os\nos.fsync(1)\nfcntl.flock(1, fcntl.LOCK_EX)",
                path="runtime/audit/synthetic_local_durability.py",
                zone_name="audit",
            ),
        )

    def test_step14_dedicated_retrieval_hat_engine_and_routing_zones_exist(self):
        expected_required_paths = {
            "retrieval": "runtime/retrieval/facade.py",
            "knowledge_engine": "runtime/knowledge/rhcsa_engine.py",
            "unix_hat": "runtime/memory_hat_registry.py",
            "knowledge_routing": "runtime/orchestrator/knowledge_router.py",
        }
        for zone, required_path in expected_required_paths.items():
            with self.subTest(zone=zone):
                resolved_paths = {
                    record.path
                    for record in self.protected_files
                    if record.zone == zone
                }
                self.assertTrue(resolved_paths)
                self.assertIn(required_path, resolved_paths)
        retrieval_paths = {
            record.path
            for record in self.protected_files
            if record.zone == "retrieval"
        }
        self.assertIn(
            "runtime/retrieval/unix_runtime_adapter.py",
            retrieval_paths,
        )

    def test_step14_knowledge_router_is_statically_no_dispatch_and_no_write(self):
        findings = step14.scan_protected_repository(
            REPO_ROOT,
            ("knowledge_routing",),
        )
        self.assertEqual("", step14.format_violations(findings))

    def test_step14_gateway_exception_is_exact_existing_and_not_protected(self):
        exceptions = step14.validate_gateway_exceptions(
            REPO_ROOT,
            self.protected_files,
        )
        self.assertEqual(("runtime/providers/gateway.py",), exceptions)
        protected_paths = {record.path for record in self.protected_files}
        self.assertTrue(all("*" not in path for path in exceptions))
        self.assertTrue(all((REPO_ROOT / path).is_file() for path in exceptions))
        self.assertFalse(protected_paths.intersection(exceptions))

    def test_step14_gateway_exception_policy_rejects_wildcards_and_protected_files(self):
        with self.assertRaises(step14.StaticCapabilityPolicyError):
            step14.validate_gateway_exceptions(
                REPO_ROOT,
                self.protected_files,
                exceptions=("runtime/providers/*.py",),
            )
        with self.assertRaises(step14.StaticCapabilityPolicyError):
            step14.validate_gateway_exceptions(
                REPO_ROOT,
                self.protected_files,
                exceptions=("runtime/artifact_preview.py",),
            )

    def test_step14_policy_sets_are_nonempty(self):
        self.assertTrue(step14.FORBIDDEN_IMPORT_ROOTS)
        self.assertTrue(step14.FORBIDDEN_CALLS)
        self.assertTrue(step14.FORBIDDEN_AUTHORITY_BOUNDARY_IMPORTS)

    def test_step14_removing_audit_ledger_from_policy_fails_closed(self):
        weakened = tuple(
            record
            for record in self.protected_files
            if record.path != "runtime/audit/durable_audit_ledger.py"
        )
        with self.assertRaises(step14.StaticCapabilityPolicyError):
            step14.validate_protected_policy(REPO_ROOT, weakened)

    def test_step14_duplicate_policy_entries_fail_closed(self):
        duplicated = (*self.protected_files, self.protected_files[0])
        with self.assertRaises(step14.StaticCapabilityPolicyError):
            step14.validate_protected_policy(REPO_ROOT, duplicated)


def scan_module(path: Path) -> StaticModuleScan:
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

    return StaticModuleScan(
        path=path,
        imports=tuple(imports),
        calls=tuple(item for item in calls if item),
    )


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
    return any(
        module_name == prefix or module_name.startswith(prefix + ".")
        for prefix in prefixes
    )


if __name__ == "__main__":
    unittest.main()
