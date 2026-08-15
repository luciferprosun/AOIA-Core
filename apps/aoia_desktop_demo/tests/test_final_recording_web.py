from __future__ import annotations

import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from apps.aoia_desktop_demo.recording_web.app import create_app
from apps.aoia_desktop_demo.recording_web.runtime import (
    DEFAULT_MODEL_ID,
    DemoEngine,
    DemoRuntimeError,
    OBSERVER_ROLES,
    ProviderCallLedger,
    _guided_case_id,
)


ROOT = Path(__file__).resolve().parents[3]
STATIC = ROOT / "apps" / "aoia_desktop_demo" / "recording_web" / "static"


class _FakeEngine(DemoEngine):
    def __init__(self) -> None:
        self.cleared = False

    @property
    def available_models(self):
        return ({"id": DEFAULT_MODEL_ID, "label": "Gemma 3 27B IT"},)

    @property
    def demo_prompt(self):
        return "Vervollständige den Satz zur BMJErnAnO."

    def accounting(self):
        return {"completed": 0, "direct_completed": 0, "cpl_completed": 0}

    def clear_conversation(self):
        self.cleared = True

    def execute(self, **request):
        request["progress"]("completed", "Response delivered.", ())
        return {
            "answer": "AIOA_DEMO_OK",
            "primary_response": "AIOA_DEMO_OK",
            "classification": "RAW_MODEL_RESPONSE",
            "verified": False,
            "evidence": [],
            "observers": [],
            "provider_calls": 1,
        }


class CallLedgerTests(unittest.TestCase):
    def test_exact_plans_and_separate_accounting(self) -> None:
        ledger = ProviderCallLedger(maximum_calls=8)
        ledger.reserve(2)
        ledger.attempted()
        ledger.finished("direct", True)
        ledger.attempted()
        ledger.finished("direct", True)
        ledger.reserve(5)
        for _ in range(5):
            ledger.attempted()
            ledger.finished("cpl", True)
        snapshot = ledger.snapshot()
        self.assertEqual(snapshot["completed"], 7)
        self.assertEqual(snapshot["direct_completed"], 2)
        self.assertEqual(snapshot["cpl_completed"], 5)

    def test_invalid_or_excess_plan_fails_closed(self) -> None:
        ledger = ProviderCallLedger(maximum_calls=5)
        with self.assertRaises(DemoRuntimeError):
            ledger.reserve(3)
        ledger.reserve(5)
        with self.assertRaises(DemoRuntimeError):
            ledger.reserve(1)


class GermanLawIntentRoutingTests(unittest.TestCase):
    def test_entry_into_force_variants_select_the_existing_primary_case(self) -> None:
        for prompt in (
            "When did the BMJErnAnO enter into force?",
            "Kiedy weszła w życie BMJErnAnO?",
            "What date did the German BMJErnAnO take effect?",
        ):
            with self.subTest(prompt=prompt):
                self.assertEqual(_guided_case_id(prompt), "primary-entry-into-force")

    def test_section_two_variant_selects_the_existing_backup_case(self) -> None:
        self.assertEqual(
            _guided_case_id("What does section II BMJErnAnO reserve for special cases?"),
            "backup-special-case-reservation",
        )

    def test_unrelated_or_ambiguous_prompt_is_not_forced_to_a_memory_hit(self) -> None:
        self.assertIsNone(_guided_case_id("When did an unrelated law enter into force?"))
        self.assertIsNone(_guided_case_id("Tell me about BMJErnAnO."))


class BrowserSurfaceContractTests(unittest.TestCase):
    def test_simple_independent_switch_surface_and_three_canonical_roles(self) -> None:
        html = (STATIC / "index.html").read_text(encoding="utf-8")
        script = (STATIC / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="model-select"', html)
        self.assertIn('id="cpl-toggle"', html)
        self.assertIn('id="knowledge-toggle"', html)
        self.assertIn('id="prompt-input"', html)
        self.assertIn('id="send-button"', html)
        self.assertIn("Shift+Enter", html)
        self.assertIn("state.roles.forEach", script)
        self.assertEqual(
            OBSERVER_ROLES,
            ("Logic & Claims", "Safety & Authority", "Evidence & Consistency"),
        )
        for forbidden in ("DIRECT", "BOUNDARY", "MEMORY MODE", "GOLDEN PATH MODE"):
            self.assertNotIn(forbidden, html)

    def test_browser_assets_do_not_contain_provider_or_database_credentials(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in STATIC.iterdir())
        for forbidden in (
            "OPENROUTER_API_KEY",
            "postgresql://",
            "cockroachdb://",
            "AWS_SECRET_ACCESS_KEY",
            "memory-patch-aioa-demo-1a/runtime",
        ):
            self.assertNotIn(forbidden, combined)
        self.assertNotIn("localStorage", combined)


class LoopbackApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = _FakeEngine()
        self.app = create_app(
            engine=self.engine,
            port=8765,
            migration_count=19,
            rls_table_count=52,
        )
        self.client = TestClient(self.app, base_url="http://127.0.0.1:8765")
        self.client.get("/")
        status = self.client.get("/api/status")
        self.assertEqual(status.status_code, 200)
        self.csrf = status.json()["csrf_token"]
        self.headers = {
            "Origin": "http://127.0.0.1:8765",
            "X-AIOA-CSRF": self.csrf,
        }

    def tearDown(self) -> None:
        self.app.state.run_store.close()
        self.client.close()

    def test_default_is_gemma_with_both_modules_off(self) -> None:
        payload = self.client.get("/api/status").json()
        self.assertEqual(payload["default_model_id"], DEFAULT_MODEL_ID)
        self.assertEqual(payload["cockroachdb"], "CONNECTED")

    def test_state_d_is_explicitly_unavailable_without_starting_a_run(self) -> None:
        response = self.client.post(
            "/api/runs",
            headers=self.headers,
            json={
                "prompt": "test",
                "model_id": DEFAULT_MODEL_ID,
                "critical_loop": True,
                "german_law": True,
                "observer_models": [DEFAULT_MODEL_ID] * 3,
            },
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "COMPOSITION_UNAVAILABLE_RECORDING_BUILD")

    def test_normal_run_completes_and_reset_clears_conversation(self) -> None:
        response = self.client.post(
            "/api/runs",
            headers=self.headers,
            json={
                "prompt": "Reply exactly",
                "model_id": DEFAULT_MODEL_ID,
                "critical_loop": False,
                "german_law": False,
                "observer_models": [],
            },
        )
        self.assertEqual(response.status_code, 202)
        run_id = response.json()["run_id"]
        projection = None
        for _ in range(50):
            projection = self.client.get(f"/api/runs/{run_id}").json()
            if projection["state"] == "COMPLETED":
                break
            time.sleep(0.01)
        self.assertEqual(projection["result"]["answer"], "AIOA_DEMO_OK")
        reset = self.client.post("/api/reset", headers=self.headers, json={})
        self.assertEqual(reset.status_code, 200)
        self.assertTrue(self.engine.cleared)

    def test_writes_require_same_origin_and_csrf(self) -> None:
        payload = {
            "prompt": "test",
            "model_id": DEFAULT_MODEL_ID,
            "critical_loop": False,
            "german_law": False,
            "observer_models": [],
        }
        self.assertEqual(self.client.post("/api/runs", json=payload).status_code, 403)
        wrong = {"Origin": "http://evil.invalid", "X-AIOA-CSRF": self.csrf}
        self.assertEqual(self.client.post("/api/runs", headers=wrong, json=payload).status_code, 403)


if __name__ == "__main__":
    unittest.main()
