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


if __name__ == "__main__":
    unittest.main()
