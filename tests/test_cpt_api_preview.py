from __future__ import annotations

import importlib
import json
import sys
import tempfile
import unittest
from contextlib import contextmanager
from http import HTTPStatus
from io import BytesIO
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = PROJECT_ROOT / "runtime"
SYNTHETIC_WEB_TOKEN = "NZ_P012_COMPAT_OPERATOR_TOKEN_001"


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
    body = json.dumps(payload).encode("utf-8")
    writes: list[tuple[HTTPStatus, dict[str, object]]] = []
    handler = object.__new__(webapp.CodexStyleHandler)
    handler.path = "/api/cpt/transform"
    handler.headers = {
        "Authorization": f"Bearer {SYNTHETIC_WEB_TOKEN}",
        "Content-Type": "application/json",
        "Content-Length": str(len(body)),
    }
    handler.rfile = BytesIO(body)
    handler.web_boundary_config = webapp.WebBoundaryConfig(
        operator_token=SYNTHETIC_WEB_TOKEN,
        allowed_origins=frozenset(),
    )
    handler._write_json = lambda status, response: writes.append((status, response))

    webapp.CodexStyleHandler.do_POST(handler)

    return writes[0]


@contextmanager
def temporary_cwd(path: Path):
    import os

    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class CptApiPreviewTests(unittest.TestCase):
    def test_cpt_transform_endpoint_returns_transformed_prompt(self) -> None:
        status, payload = post_cpt_transform({"prompt": "Review my deployment plan.", "mode": "balanced_critic"})

        self.assertEqual(HTTPStatus.OK, status)
        self.assertTrue(payload["ok"])
        record = payload["record"]
        self.assertTrue(record["transformed_prompt"])
        self.assertIn("critical review", record["transformed_prompt"])
        self.assertIn("not canonical truth", record["transformed_prompt"])

    def test_cpt_transform_endpoint_rejects_empty_prompt(self) -> None:
        status, payload = post_cpt_transform({"prompt": "   ", "mode": "balanced_critic"})

        self.assertEqual(HTTPStatus.BAD_REQUEST, status)
        self.assertFalse(payload["ok"])
        self.assertIn("prompt", payload["error"])

    def test_cpt_transform_endpoint_preserves_safety_flags(self) -> None:
        status, payload = post_cpt_transform({"prompt": "Review this incident response.", "mode": "balanced_critic"})

        self.assertEqual(HTTPStatus.OK, status)
        record = payload["record"]
        self.assertFalse(record["provider_call_permitted"])
        self.assertFalse(record["execution_permitted"])
        self.assertFalse(record["browser_action_permitted"])
        self.assertTrue(record["human_review_required"])
        self.assertIn(record["canonical_status"], {"DRAFT", "NOT_CANONICAL"})

    def test_cpt_transform_endpoint_rejects_non_balanced_mode(self) -> None:
        status, payload = post_cpt_transform({"prompt": "Review this.", "mode": "epistemic_auditor"})

        self.assertEqual(HTTPStatus.BAD_REQUEST, status)
        self.assertFalse(payload["ok"])
        self.assertIn("balanced_critic", payload["error"])

    def test_cpt_transform_endpoint_does_not_call_provider_router_or_tools(self) -> None:
        webapp = import_or_reload_webapp()
        with (
            patch.object(webapp, "get_service", side_effect=AssertionError("get_service called")) as get_service,
            patch.dict(
                sys.modules,
                {
                    "model_router": None,
                    "runtime.model_router": None,
                    "provider_clients": None,
                    "runtime.provider_clients": None,
                    "runtime.tools.browser_tools": None,
                    "runtime.tools.shell_tools": None,
                    "runtime.tools.executor": None,
                },
            ),
        ):
            status, payload = post_cpt_transform({"prompt": "Review this rollout."}, webapp=webapp)

        self.assertEqual(HTTPStatus.OK, status)
        self.assertTrue(payload["ok"])
        get_service.assert_not_called()

    def test_cpt_transform_endpoint_does_not_write_audit_log_automatically(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            with temporary_cwd(temp_path), patch("runtime.cpt.audit.append_transformation_record") as append_record:
                status, payload = post_cpt_transform({"prompt": "Review this audit behavior."})

            self.assertEqual(HTTPStatus.OK, status)
            self.assertTrue(payload["ok"])
            append_record.assert_not_called()
            self.assertEqual([], list(temp_path.rglob("*.jsonl")))


if __name__ == "__main__":
    unittest.main()
