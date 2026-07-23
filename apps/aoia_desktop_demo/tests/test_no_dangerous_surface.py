"""Static checks that the demo package has no execution/tool surface and
does not import the production runtime's dangerous execution modules.

These are plain text/import checks, not behavioral tests, but they are
cheap, fast, and directly enforce several of the demo's non-negotiable
boundaries at the source level.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]  # apps/aoia_desktop_demo
HATS_ROOT = PACKAGE_ROOT / "knowledge" / "hats"

FORBIDDEN_IMPORT_PREFIXES = (
    "subprocess",
    "runtime.git_ops",
    "runtime.browser_ops",
    "runtime.package_ops",
    "runtime.patches",
    "runtime.execution",
    "runtime.agent_loops",
    "runtime.tools.shell_tools",
    "runtime.tools.executor",
    "runtime.tools.browser_tools",
    "runtime.integration_boundaries",
    "runtime.providers",  # the production provider-gate machinery; the demo has its own
    "git_ops",
    "browser_ops",
    "package_ops",
    "patches",
    "agent_loops",
)

FORBIDDEN_CALL_NAMES = ("eval", "exec", "compile", "os.system", "os.popen")


def _iter_python_files():
    for path in PACKAGE_ROOT.rglob("*.py"):
        if "tests" in path.parts:
            continue
        yield path


def _call_name(node: ast.Call) -> str:
    parts: list[str] = []
    value = node.func
    while isinstance(value, ast.Attribute):
        parts.append(value.attr)
        value = value.value
    if isinstance(value, ast.Name):
        parts.append(value.id)
    return ".".join(reversed(parts))


class NoDangerousSurfaceTests(unittest.TestCase):
    def test_no_forbidden_runtime_imports(self) -> None:
        offenders = []
        for path in _iter_python_files():
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                for name in names:
                    if any(name == prefix or name.startswith(prefix + ".") for prefix in FORBIDDEN_IMPORT_PREFIXES):
                        offenders.append((str(path.relative_to(PACKAGE_ROOT)), name))
        self.assertEqual(offenders, [], f"forbidden imports found: {offenders}")

    def test_no_subprocess_shell_or_eval_usage(self) -> None:
        offenders = []
        for path in _iter_python_files():
            text = path.read_text(encoding="utf-8")
            for forbidden in ("subprocess.", "os.system(", "os.popen(", "eval(", "exec("):
                if forbidden in text:
                    offenders.append((str(path.relative_to(PACKAGE_ROOT)), forbidden))
        self.assertEqual(offenders, [], f"forbidden calls found: {offenders}")

    def test_no_write_calls_into_the_knowledge_index(self) -> None:
        # Call-shaped patterns only (trailing "(") so descriptive comments
        # and docstrings that mention "rebuild"/"ingest" in prose (e.g.
        # "never calls anything that rebuilds...") do not false-positive.
        knowledge_dir = PACKAGE_ROOT / "knowledge"
        offenders = []
        for path in knowledge_dir.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for forbidden in ("write_text(", "write_bytes(", ".unlink(", "shutil.", "rebuild(", "ingest("):
                if forbidden in text:
                    offenders.append((str(path.relative_to(PACKAGE_ROOT)), forbidden))
        self.assertEqual(offenders, [], f"the knowledge adapter must stay strictly read-only: {offenders}")

    def test_settings_module_has_no_network_or_execution_calls(self) -> None:
        text = (PACKAGE_ROOT / "state" / "settings.py").read_text(encoding="utf-8")
        for forbidden in ("urllib", "socket", "subprocess"):
            self.assertNotIn(forbidden, text)

    def test_knowledge_hat_package_has_no_forbidden_capability_imports(self) -> None:
        forbidden_prefixes = (
            "subprocess",
            "socket",
            "requests",
            "httpx",
            "urllib",
            "webbrowser",
            "selenium",
            "playwright",
            "git",
            "github",
            "openai",
            "anthropic",
            "pip",
            "setuptools",
            "importlib",
        )
        offenders = []
        for path in HATS_ROOT.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                names: list[str] = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                for name in names:
                    if any(
                        name == prefix or name.startswith(prefix + ".")
                        for prefix in forbidden_prefixes
                    ):
                        offenders.append((path.name, name))
        self.assertEqual(offenders, [])

    def test_knowledge_hat_package_has_no_execution_dynamic_loading_or_write_calls(self) -> None:
        forbidden_calls = {
            "eval",
            "exec",
            "compile",
            "__import__",
            "os.system",
            "os.popen",
            "subprocess.Popen",
            "subprocess.run",
            "subprocess.call",
            "importlib.import_module",
            "webbrowser.open",
        }
        forbidden_methods = {
            "write_text",
            "write_bytes",
            "unlink",
            "mkdir",
            "makedirs",
            "rename",
            "touch",
        }
        offenders = []
        for path in HATS_ROOT.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                name = _call_name(node)
                if name in forbidden_calls or name.rsplit(".", 1)[-1] in forbidden_methods:
                    offenders.append((path.name, name))
                if name.rsplit(".", 1)[-1] == "open":
                    mode = None
                    if node.args and isinstance(node.args[0], ast.Constant):
                        mode = node.args[0].value
                    for keyword in node.keywords:
                        if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
                            mode = keyword.value.value
                    if isinstance(mode, str) and any(flag in mode for flag in "wax+"):
                        offenders.append((path.name, f"{name}({mode!r})"))
        self.assertEqual(offenders, [])

    def test_knowledge_hat_package_does_not_mutate_sys_path(self) -> None:
        offenders = []
        for path in HATS_ROOT.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for forbidden in (
                "sys.path.append",
                "sys.path.insert",
                "sys.path.extend",
                "sys.path =",
            ):
                if forbidden in text:
                    offenders.append((path.name, forbidden))
        self.assertEqual(offenders, [])

    def test_controller_has_only_the_generic_hat_boundary(self) -> None:
        source = (PACKAGE_ROOT / "app.py").read_text(encoding="utf-8")
        for forbidden in (
            "GermanFederalEmploymentWorkerLawAdapter",
            "retrieve_linux_evidence",
            "german_federal_employment_worker_law.py",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn("HatAttachmentService", source)

    def test_public_hat_map_and_example_contain_no_private_machine_path_or_secret(self) -> None:
        repository_root = PACKAGE_ROOT.parents[1]
        paths = (
            repository_root / "docs" / "KNOWLEDGE_HAT_INTEGRATION_MAP.md",
            repository_root / "config" / "knowledge_hats" / "local_bindings.example.json",
            *HATS_ROOT.rglob("*.json"),
        )
        for path in paths:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(str(Path.home()), text)
            self.assertNotIn("sk-" + "or-", text)
            self.assertLess(path.stat().st_size, 1_000_000)
        ignore_text = (repository_root / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("/config/knowledge_hats/local_bindings.json", ignore_text)
        self.assertIn("/.hat_bindings.json", ignore_text)


if __name__ == "__main__":
    unittest.main()
