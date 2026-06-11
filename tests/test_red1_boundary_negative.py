from __future__ import annotations

import importlib
import importlib.util
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
import urllib.request
import webbrowser
from collections.abc import Iterable
from contextlib import ExitStack, contextmanager
from http import HTTPStatus
from io import BytesIO
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = PROJECT_ROOT / "runtime"
WEB_DIR = PROJECT_ROOT / "web"

BROWSER_MODULES = {
    "runtime.tools.browser_tools",
    "runtime.tools.web_reader",
    "playwright",
    "selenium",
}
EXECUTION_MODULES = {
    "runtime.provider_clients",
    "runtime.model_router",
    "provider_clients",
    "model_router",
    "runtime.tools.shell_tools",
    "shell_tools",
}

LIVE_BYPASS_TOKENS = (
    "require_approval=False",
    "human_approval_required=False",
    "execution_permitted=True",
    "auto_approve",
    "skip_approval",
    "bypass_approval",
    "timeout_as_approval",
)


def import_or_reload_webapp():
    runtime_path = str(RUNTIME_DIR)
    inserted = False
    if runtime_path not in sys.path:
        sys.path.insert(0, runtime_path)
        inserted = True
    try:
        if "runtime.webapp" in sys.modules:
            return importlib.reload(sys.modules["runtime.webapp"])
        return importlib.import_module("runtime.webapp")
    finally:
        if inserted:
            try:
                sys.path.remove(runtime_path)
            except ValueError:
                pass


def post_cpt_transform(payload: dict, webapp=None):
    if webapp is None:
        webapp = import_or_reload_webapp()
    body = __import__("json").dumps(payload).encode("utf-8")
    writes: list[tuple[HTTPStatus, dict[str, object]]] = []
    handler = object.__new__(webapp.CodexStyleHandler)
    handler.path = "/api/cpt/transform"
    handler.headers = {"Content-Length": str(len(body))}
    handler.rfile = BytesIO(body)
    handler._write_json = lambda status, response: writes.append((status, response))

    webapp.CodexStyleHandler.do_POST(handler)

    return writes[0]


@contextmanager
def patched_dangerous_primitives():
    stack = ExitStack()
    mocks = {
        "subprocess_run": stack.enter_context(
            patch.object(subprocess, "run", side_effect=AssertionError("subprocess.run called"))
        ),
        "subprocess_popen": stack.enter_context(
            patch.object(subprocess, "Popen", side_effect=AssertionError("subprocess.Popen called"))
        ),
        "os_system": stack.enter_context(
            patch.object(os, "system", side_effect=AssertionError("os.system called"))
        ),
        "urlopen": stack.enter_context(
            patch.object(
                urllib.request,
                "urlopen",
                side_effect=AssertionError("urllib.request.urlopen called"),
            )
        ),
        "socket": stack.enter_context(
            patch.object(
                socket,
                "create_connection",
                side_effect=AssertionError("socket.create_connection called"),
            )
        ),
        "webbrowser": stack.enter_context(
            patch.object(webbrowser, "open", side_effect=AssertionError("webbrowser.open called"))
        ),
        "write_text": stack.enter_context(
            patch.object(Path, "write_text", side_effect=AssertionError("Path.write_text called"))
        ),
        "write_bytes": stack.enter_context(
            patch.object(Path, "write_bytes", side_effect=AssertionError("Path.write_bytes called"))
        ),
        "unlink": stack.enter_context(
            patch.object(Path, "unlink", side_effect=AssertionError("Path.unlink called"))
        ),
        "shutil_move": stack.enter_context(
            patch.object(shutil, "move", side_effect=AssertionError("shutil.move called"))
        ),
        "shutil_rmtree": stack.enter_context(
            patch.object(shutil, "rmtree", side_effect=AssertionError("shutil.rmtree called"))
        ),
    }

    try:
        importlib.util.find_spec("requests")
    except ModuleNotFoundError:
        requests = None
    else:
        requests = importlib.import_module("requests")
    if requests is not None:
        mocks["requests_get"] = stack.enter_context(
            patch.object(requests, "get", side_effect=AssertionError("requests.get called"))
        )
        mocks["requests_post"] = stack.enter_context(
            patch.object(requests, "post", side_effect=AssertionError("requests.post called"))
        )

    try:
        yield stack, mocks
    finally:
        stack.close()


def browser_modules_loaded() -> set[str]:
    return BROWSER_MODULES.intersection(sys.modules)


def execution_modules_loaded() -> set[str]:
    return EXECUTION_MODULES.intersection(sys.modules)


def live_runtime_and_web_files() -> Iterable[Path]:
    roots = [
        RUNTIME_DIR,
        WEB_DIR,
    ]
    skip_parts = {
        ".venv",
        "__pycache__",
        "knowledge",
        "reports",
        "candidates",
        "source",
        "extracted",
    }
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in skip_parts for part in path.parts):
                continue
            if path.suffix not in {".py", ".js", ".html", ".css", ".json"}:
                continue
            yield path


class Red1BoundaryNegativeTests(unittest.TestCase):
    def test_webapp_import_does_not_pull_browser_or_execution_modules(self) -> None:
        before_browser = browser_modules_loaded()
        before_execution = execution_modules_loaded()
        with patched_dangerous_primitives() as (stack, mocks):
            with stack:
                module = import_or_reload_webapp()

        self.assertTrue(hasattr(module, "CodexStyleHandler"))
        self.assertTrue(hasattr(module, "build_cpt_transform_payload"))
        self.assertFalse(browser_modules_loaded() - before_browser)
        self.assertFalse(execution_modules_loaded() - before_execution)
        for mock in mocks.values():
            mock.assert_not_called()

    def test_cpt_transform_endpoint_does_not_touch_browser_shell_provider_file_or_git_primitives(self) -> None:
        before_browser = browser_modules_loaded()
        before_execution = execution_modules_loaded()
        with patched_dangerous_primitives() as (stack, mocks):
            with stack:
                webapp = import_or_reload_webapp()
                status, payload = post_cpt_transform(
                    {"prompt": "Review my AOIA runtime boundary plan.", "mode": "balanced_critic"},
                    webapp=webapp,
                )

        self.assertEqual(HTTPStatus.OK, status)
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["record"]["provider_call_permitted"])
        self.assertFalse(payload["record"]["execution_permitted"])
        self.assertFalse(payload["record"]["browser_action_permitted"])
        self.assertFalse(browser_modules_loaded() - before_browser)
        self.assertFalse(execution_modules_loaded() - before_execution)
        for mock in mocks.values():
            mock.assert_not_called()

    def test_cpt_transform_endpoint_does_not_auto_write_audit_or_mutate_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            with patch("runtime.cpt.audit.append_transformation_record") as append_record:
                with patched_dangerous_primitives() as (stack, mocks):
                    with stack:
                        with patch.object(Path, "open", wraps=Path.open):
                            webapp = import_or_reload_webapp()
                            with self.subTest("endpoint call"):
                                status, payload = post_cpt_transform(
                                    {"prompt": "Review this transform path.", "mode": "balanced_critic"},
                                    webapp=webapp,
                                )

            self.assertEqual(HTTPStatus.OK, status)
            self.assertTrue(payload["ok"])
            append_record.assert_not_called()
            for mock in mocks.values():
                mock.assert_not_called()
            self.assertFalse(list(temp_path.rglob("*.jsonl")))

    def test_cpt_transform_endpoint_rejects_live_bypass_tokens_in_runtime_web_files(self) -> None:
        findings: list[tuple[str, str]] = []
        for path in live_runtime_and_web_files():
            text = path.read_text(encoding="utf-8")
            hits = [token for token in LIVE_BYPASS_TOKENS if token in text]
            for token in hits:
                findings.append((str(path), token))

        self.assertEqual(
            [],
            findings,
            f"dangerous bypass tokens must not appear in live runtime/web files: {findings}",
        )

    def test_cpt_transform_prompt_path_does_not_require_browser_or_provider_imports(self) -> None:
        before_browser = browser_modules_loaded()
        before_execution = execution_modules_loaded()
        with patched_dangerous_primitives() as (stack, mocks):
            with stack:
                webapp = import_or_reload_webapp()
                record = webapp.build_cpt_transform_payload(
                    "Review this rollout critically.", mode="balanced_critic"
                )

        self.assertTrue(record["ok"])
        self.assertEqual("balanced_critic", record["record"]["critic_mode"])
        self.assertFalse(record["record"]["provider_call_permitted"])
        self.assertFalse(record["record"]["execution_permitted"])
        self.assertFalse(record["record"]["browser_action_permitted"])
        self.assertFalse(browser_modules_loaded() - before_browser)
        self.assertFalse(execution_modules_loaded() - before_execution)
        for mock in mocks.values():
            mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
