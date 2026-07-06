from __future__ import annotations

import unittest
from pathlib import Path

from runtime.model_catalog import (
    CATALOG_NOTICE,
    get_static_model_catalog,
    get_static_model_catalog_payload,
)
from runtime.schemas.model_router import (
    ModelCatalogEntry,
    ProviderClass,
    RoutingDecisionStatus,
    TrustLevel,
)
from runtime.webapp import route_get_payload


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = PROJECT_ROOT / "runtime" / "model_catalog.py"
WEBAPP_PATH = PROJECT_ROOT / "runtime" / "webapp.py"
APP_JS_PATH = PROJECT_ROOT / "web" / "app.js"
INDEX_PATH = PROJECT_ROOT / "web" / "index.html"


class ModelCatalogPreviewTests(unittest.TestCase):
    def test_static_catalog_returns_inert_tuple_entries(self) -> None:
        catalog = get_static_model_catalog()

        self.assertIsInstance(catalog, tuple)
        self.assertGreaterEqual(len(catalog), 4)
        self.assertTrue(all(isinstance(entry, ModelCatalogEntry) for entry in catalog))
        self.assertTrue(all(entry.enabled is False for entry in catalog))
        self.assertTrue(all(entry.allows_sensitive_tasks is False for entry in catalog))
        self.assertTrue(all(entry.allows_canonical_tasks is False for entry in catalog))

    def test_catalog_contains_expected_provider_classes(self) -> None:
        provider_classes = {entry.provider_class for entry in get_static_model_catalog()}

        self.assertIn(ProviderClass.GEMINI, provider_classes)
        self.assertIn(ProviderClass.OPENROUTER, provider_classes)
        self.assertIn(ProviderClass.OPENROUTER_FREE, provider_classes)
        self.assertIn(ProviderClass.LOCAL_MODEL, provider_classes)
        self.assertIn(ProviderClass.DISABLED, provider_classes)

    def test_free_model_entries_are_development_only_and_not_sensitive_or_canonical(self) -> None:
        free_entries = [
            entry
            for entry in get_static_model_catalog()
            if entry.provider_class is ProviderClass.OPENROUTER_FREE
            or entry.trust_level is TrustLevel.THIRD_PARTY_FREE
            or entry.free_tier
        ]

        self.assertTrue(free_entries)
        for entry in free_entries:
            self.assertFalse(entry.enabled)
            self.assertFalse(entry.allows_sensitive_tasks)
            self.assertFalse(entry.allows_canonical_tasks)
            self.assertTrue(any("Development-only" in note for note in entry.notes))

    def test_payload_states_preview_only_boundaries(self) -> None:
        payload = get_static_model_catalog_payload()

        self.assertEqual(CATALOG_NOTICE, payload["notice"])
        self.assertEqual(RoutingDecisionStatus.REQUIRES_HUMAN_APPROVAL.value, payload["status"])
        self.assertFalse(payload["provider_call_permitted"])
        self.assertFalse(payload["automatic_fallback_permitted"])
        self.assertFalse(payload["health_check_permitted"])
        self.assertFalse(payload["canonical_promotion_permitted"])
        self.assertIsInstance(payload["models"], list)
        self.assertTrue(payload["models"])

    def test_payload_serializes_enums_as_strings(self) -> None:
        payload = get_static_model_catalog_payload()

        for entry in payload["models"]:
            self.assertIsInstance(entry["provider_class"], str)
            self.assertIsInstance(entry["trust_level"], str)
            self.assertIsInstance(entry["notes"], list)

    def test_webapp_exposes_read_only_catalog_endpoint(self) -> None:
        source = WEBAPP_PATH.read_text(encoding="utf-8")
        status, payload = route_get_payload("/api/model-catalog")

        self.assertEqual(200, status)
        self.assertTrue(payload["models"])
        self.assertIn('path == "/api/model-catalog"', source)
        self.assertIn("get_static_model_catalog_payload()", source)
        self.assertNotIn('"/api/model-catalog":\n                prompt', source)

    def test_frontend_contains_required_safety_wording(self) -> None:
        index_source = INDEX_PATH.read_text(encoding="utf-8")
        app_source = APP_JS_PATH.read_text(encoding="utf-8")

        self.assertIn("Preview only", index_source)
        self.assertIn("no provider calls", index_source)
        self.assertIn("Human approval required before any future provider call", index_source)
        self.assertIn("/api/router/status", app_source)

    def test_catalog_module_contains_no_forbidden_implementation_imports_or_terms(self) -> None:
        source = CATALOG_PATH.read_text(encoding="utf-8")
        forbidden_terms = (
            "subprocess",
            "os.system",
            "Popen",
            "requests",
            "httpx",
            "urllib",
            "exec(",
            "eval(",
            "openai",
            "anthropic",
            "import google",
            "from google",
            "os.environ",
            "getenv",
            "browser_tools",
            "web_reader",
            "shell_tools",
            "def health_check",
            "def call_model",
            "def route",
            "def execute",
            "def run",
        )
        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
