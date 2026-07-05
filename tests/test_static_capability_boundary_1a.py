from __future__ import annotations

import ast
import unittest
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

CORE_NO_AUTHORITY_MODULES = (
    "runtime/artifact_preview.py",
    "runtime/providers/critic.py",
    "runtime/providers/critic_taxonomy.py",
    "runtime/providers/critic_adversarial_corpus.py",
    "runtime/providers/provider_gateway_guard.py",
    "runtime/providers/provider_payload_governance.py",
    "runtime/providers/provider_response_schema.py",
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
