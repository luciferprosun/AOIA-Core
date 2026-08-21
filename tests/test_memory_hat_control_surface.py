from __future__ import annotations

import importlib
import sys
import unittest
from http import HTTPStatus
from pathlib import Path

from runtime.memory_hat_registry import get_memory_hat_payload, get_memory_hats


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = PROJECT_ROOT / "runtime"
REGISTRY_PATH = RUNTIME_DIR / "memory_hat_registry.py"
WEBAPP_PATH = RUNTIME_DIR / "webapp.py"
SYNTHETIC_WEB_TOKEN = "NZ_P012_COMPAT_OPERATOR_TOKEN_003"

FORBIDDEN_IMPORTS = {
    "runtime.tools.browser_tools",
    "runtime.tools.web_reader",
    "runtime.tools.shell_tools",
    "runtime.tools.executor",
    "runtime.provider_clients",
    "runtime.providers",
    "provider_clients",
    "providers",
    "playwright",
    "selenium",
}

EXPECTED_HATS = {
    "hat_001": ("Hat 001 - Bash Safety", "ACTIVE_CORE"),
    "hat_002": ("Hat 002 - Linux/RHCSA", "ACTIVE_KNOWLEDGE"),
    "hat_003": ("Hat 003 - Python", "DRAFT_KNOWLEDGE"),
    "hat_004": ("Hat 004 - Browser Governance", "FROZEN_GOVERNANCE"),
}

REQUIRED_FIELDS = {
    "hat_id",
    "name",
    "domain",
    "status",
    "purpose",
    "canonical_paths",
    "candidate_paths",
    "runtime_visible",
    "execution_allowed",
    "human_review_required",
    "promotion_policy",
    "notes",
}


def loaded_forbidden_modules() -> set[str]:
    return FORBIDDEN_IMPORTS.intersection(sys.modules)


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


class MemoryHatControlSurfaceTests(unittest.TestCase):
    def test_registry_contains_exactly_required_memory_hats(self) -> None:
        hats = get_memory_hats()

        self.assertEqual(set(EXPECTED_HATS), {hat.hat_id for hat in hats})
        self.assertEqual(4, len(hats))
        for hat in hats:
            expected_name, expected_status = EXPECTED_HATS[hat.hat_id]
            self.assertEqual(expected_name, hat.name)
            self.assertEqual(expected_status, hat.status)

    def test_all_memory_hats_are_inert_and_human_review_required(self) -> None:
        for hat in get_memory_hats():
            with self.subTest(hat_id=hat.hat_id):
                self.assertFalse(hat.execution_allowed)
                self.assertTrue(hat.human_review_required)
                self.assertTrue(hat.runtime_visible)

    def test_payload_has_required_fields_and_static_control_surface_notice(self) -> None:
        payload = get_memory_hat_payload()

        self.assertTrue(payload["ok"])
        self.assertEqual("AIOA White Hat", payload["product"])
        self.assertEqual(False, payload["execution_allowed"])
        self.assertEqual(True, payload["human_review_required"])
        self.assertIn("do not execute actions", str(payload["notice"]))
        for hat in payload["hats"]:
            self.assertEqual(REQUIRED_FIELDS, set(hat))
            self.assertFalse(hat["execution_allowed"])
            self.assertTrue(hat["human_review_required"])

    def test_registry_import_does_not_load_forbidden_runtime_surfaces(self) -> None:
        before = loaded_forbidden_modules()
        importlib.reload(importlib.import_module("runtime.memory_hat_registry"))
        after = loaded_forbidden_modules()

        self.assertFalse(after - before, f"memory hat registry imported forbidden modules: {sorted(after - before)}")

    def test_registry_source_has_no_forbidden_execution_or_provider_imports(self) -> None:
        source = REGISTRY_PATH.read_text(encoding="utf-8")

        forbidden_terms = (
            "browser_tools",
            "web_reader",
            "shell_tools",
            "executor",
            "provider_clients",
            "providers",
            "playwright",
            "selenium",
            "subprocess",
            "urlopen",
            "requests.",
        )
        offenders = [term for term in forbidden_terms if term in source]
        self.assertEqual([], offenders)

    def test_webapp_exposes_read_only_memory_hats_endpoint(self) -> None:
        source = WEBAPP_PATH.read_text(encoding="utf-8")

        self.assertIn('"/api/memory-hats"', source)
        self.assertIn("AUTHENTICATED_READ_PATHS", source)
        self.assertIn("get_memory_hat_payload()", source)

    def test_memory_hats_endpoint_returns_registry_payload_without_server_start(self) -> None:
        before = loaded_forbidden_modules()
        webapp = import_or_reload_webapp()
        after = loaded_forbidden_modules()
        writes: list[tuple[HTTPStatus, dict[str, object]]] = []
        handler = object.__new__(webapp.CodexStyleHandler)
        handler.path = "/api/memory-hats"
        handler.headers = {
            "Authorization": f"Bearer {SYNTHETIC_WEB_TOKEN}",
        }
        handler.web_boundary_config = webapp.WebBoundaryConfig(
            operator_token=SYNTHETIC_WEB_TOKEN,
            allowed_origins=frozenset(),
        )
        handler._write_json = lambda status, payload: writes.append((status, payload))

        webapp.CodexStyleHandler.do_GET(handler)

        self.assertFalse(after - before, f"memory hats API import loaded forbidden modules: {sorted(after - before)}")
        self.assertEqual(1, len(writes))
        status, payload = writes[0]
        self.assertEqual(HTTPStatus.OK, status)
        payload_without_http_identity = dict(payload)
        payload_without_http_identity.pop("request_id")
        payload_without_http_identity.pop("trace_id")
        self.assertEqual(get_memory_hat_payload(), payload_without_http_identity)


if __name__ == "__main__":
    unittest.main()
