from __future__ import annotations

import json
import threading
import time
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from apps.aoia_desktop_demo.recording_web.app import create_app
from apps.aoia_desktop_demo.recording_web import cockroach_runtime
from apps.aoia_desktop_demo.recording_web.runtime import (
    DEFAULT_MODEL_ID,
    DemoEngine,
    DemoRuntimeError,
    EvidenceProjection,
    KnowledgeRetrieval,
    OBSERVER_ROLES,
    ProviderCallLedger,
)
from apps.aoia_desktop_demo.recording_web.nachwg_hat import (
    HatAuditResult,
    audit_response,
    load_pack,
    postcheck_final,
)
from apps.aoia_desktop_demo.providers.base import ChatResult


ROOT = Path(__file__).resolve().parents[3]
STATIC = ROOT / "apps" / "aoia_desktop_demo" / "recording_web" / "static"
PACK = (
    ROOT
    / "apps"
    / "aoia_desktop_demo"
    / "recording_web"
    / "data"
    / "german_nachwg_hard_knowledge_2026.json"
)


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


class NachwGPackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pack = json.loads(PACK.read_text(encoding="utf-8"))

    def test_exact_atomic_counts_fingerprint_and_unique_ids(self) -> None:
        records = self.pack["records"]
        self.assertEqual(len(records), 36)
        self.assertEqual(sum(value["status"] == "CURRENT" for value in records), 31)
        self.assertEqual(sum(value["status"] == "SUPERSEDED" for value in records), 5)
        self.assertEqual(len({value["knowledge_id"] for value in records}), 36)
        self.assertEqual(
            self.pack["source_package"]["pdf_sha256"],
            "fe70b8eaa3a578d17d6578f477526c2642bb0d2fce2d206e9fd3bfb22f614311",
        )

    def test_temporal_intervals_do_not_back_project_textform(self) -> None:
        records = {value["knowledge_id"]: value for value in self.pack["records"]}

        def applicable(record, as_of):
            start = record["temporal_facts"]["effective_from"][:10]
            end = record["temporal_facts"].get("effective_to")
            return start <= as_of and (end is None or as_of < end[:10])

        self.assertTrue(applicable(records["DE-NACHWG-PAPER-2022-2024"], "2024-07-22"))
        self.assertFalse(applicable(records["DE-NACHWG-TEXTFORM-2025-001"], "2024-07-22"))
        self.assertFalse(applicable(records["DE-NACHWG-PAPER-2022-2024"], "2026-07-22"))
        self.assertTrue(applicable(records["DE-NACHWG-TEXTFORM-2025-001"], "2026-07-22"))

    def test_guardrails_and_demo_prompt_are_present(self) -> None:
        identifiers = {value["knowledge_id"] for value in self.pack["records"]}
        self.assertTrue(
            {
                "DE-BGB-630-IRRELEVANT-001",
                "DE-BGB-630A-IRRELEVANT-001",
                "DE-NACHWG-DUTY-2022-001",
            }.issubset(identifiers)
        )
        self.assertIn("Today is 22 July 2026", self.pack["demo_prompt"])


class CockroachSeedContractTests(unittest.TestCase):
    def test_atomic_records_are_exact_snapshot_bytes_not_claimed_as_pdf_bytes(self) -> None:
        entries = cockroach_runtime._nachwg_seed_entries(
            cockroach_runtime._load_nachwg_pack()
        )
        self.assertEqual(len(entries), 36)
        self.assertTrue(
            all(entry["registry"].artifact.exact_source_bytes for entry in entries)
        )
        self.assertTrue(
            all(
                entry["registry"].scope.additional_dimensions[
                    "not_authentic_promulgation"
                ]
                for entry in entries
            )
        )
        self.assertTrue(
            all(
                entry["metadata"]["temporal_facts"]["supersedes"] == []
                and entry["metadata"]["temporal_facts"]["superseded_by"] == []
                and "supersedes" not in entry["metadata"]
                and "superseded_by" not in entry["metadata"]
                for entry in entries
            )
        )
        self.assertTrue(
            any(entry["metadata"]["declared_supersedes"] for entry in entries)
        )

    def test_import_uses_one_sql_api_transaction_and_replays_idempotently(self) -> None:
        class Root:
            calls = []

            @staticmethod
            def _statements(sql):
                return (sql,)

            def execute_results(self, database, statements, **options):
                self.calls.append((database, statements, options))

        root = Root()
        plans = (
            {"insert": 36, "unchanged": 0, "conflict": 0},
            {"insert": 0, "unchanged": 36, "conflict": 0},
        )
        with patch.object(
            cockroach_runtime,
            "_nachwg_import_plan",
            side_effect=plans,
        ):
            result = cockroach_runtime._seed_nachwg_hard_knowledge(root, "test_db")
        self.assertEqual(result["added"], 36)
        self.assertEqual(len(root.calls), 1)
        self.assertEqual(root.calls[0][2]["separate_transactions"], False)


class DeterministicHatTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pack = load_pack()
        self.evidence = tuple(
            value for value in self.pack["records"] if value["status"] == "CURRENT"
        )

    def test_wrong_primary_is_audited_not_answered_by_hat(self) -> None:
        primary = (
            "CONTRACT STATUS: INVALID\n"
            "NO EMPLOYMENT CONDITIONS DOCUMENT: PERMITTED\n"
            "PAPER WITH A HANDWRITTEN SIGNATURE ALWAYS REQUIRED: YES\n"
            "CAN A PDF OR EMAIL BE SUFFICIENT: NO\n"
            "The duty follows from §630 and §630a BGB."
        )
        audit = audit_response(
            primary,
            self.evidence,
            "2026-07-22",
            self.pack["demo_prompt"],
        )
        self.assertEqual(audit.verdict, "CORRECTION_REQUIRED")
        self.assertGreaterEqual(len(audit.corrections), 4)
        encoded = json.dumps(audit.as_dict(), ensure_ascii=False)
        self.assertIn("§2 NachwG", encoded)
        self.assertIn("DE-BGB-630A-IRRELEVANT-001", encoded)

    def test_complete_final_passes_same_deterministic_postcheck(self) -> None:
        final = (
            "CONTRACT STATUS: VALID\n"
            "NO EMPLOYMENT CONDITIONS DOCUMENT: NOT PERMITTED\n"
            "PAPER WITH A HANDWRITTEN SIGNATURE ALWAYS REQUIRED: NO\n"
            "CAN A PDF OR EMAIL BE SUFFICIENT: DEPENDS\n\n"
            "An ordinary open-ended oral employment contract is generally valid "
            "under §105 GewO and §611a BGB, but §2 NachwG imposes a separate "
            "documentation obligation. Items 1, 7 and 8 are due on the first day; "
            "items 2–6, 9 and 10 within seven days; items 11–15 within one month. "
            "Since 2025, §126b BGB Textform can work if the document is accessible, "
            "storable and printable and the employer requests confirmation of "
            "receipt. The employee may still demand a written signed record, and "
            "Textform is unavailable in §2a SchwarzArbG sectors. Thus a PDF/email "
            "only conditionally suffices; QES is not required. Specified breaches "
            "can trigger a fine up to EUR 2,000 under §4 NachwG."
        )
        audit = audit_response(
            final,
            self.evidence,
            "2026-07-22",
            self.pack["demo_prompt"],
        )
        self.assertEqual(audit.verdict, "PASS")
        self.assertTrue(postcheck_final(final, audit, self.evidence))
        self.assertLessEqual(len(final.split()), 150)
        self.assertFalse(
            postcheck_final(
                final + "\n" + "additional " * 151,
                audit,
                self.evidence,
            )
        )


class _ResponseCentricKnowledge:
    def __init__(self, events: list[tuple[str, str]]) -> None:
        self.events = events

    @property
    def finalization_requirements(self):
        return {
            "contract_status": "VALID",
            "maximum_explanation_words": 150,
            "required_statutory_basis": ["§2 NachwG"],
        }

    def finalization_evidence(self, evidence):
        return [value.as_dict() for value in evidence]

    def retrieve_for_response(self, *, user_prompt, draft_response, request_id):
        self.events.append(("retrieval", draft_response))
        evidence = (
            EvidenceProjection(
                source_id="nachwg-test-source",
                official_identifier="DE-NACHWG-HARD-KNOWLEDGE-2026",
                provision="DE-NACHWG-DUTY-2022-001",
                authority="AUTHORITATIVE_SECONDARY",
                excerpt="KNOWLEDGE_SCOPE: German Law / NachwG\nRULE: §2 NachwG applies.",
                source_reference="pdf:test",
                item_hash="a" * 64,
                metadata={
                    "knowledge_id": "DE-NACHWG-DUTY-2022-001",
                    "topic": "Separate evidence duty",
                    "status": "CURRENT",
                    "statutory_basis": ["§2 NachwG"],
                },
            ),
        )
        return KnowledgeRetrieval(
            scenario_date=datetime(2026, 7, 22, tzinfo=UTC),
            evidence=evidence,
            step18_count=36,
            step20_count=36,
            applicable_count=31,
        )


class _ResponseCentricProvider:
    def __init__(self, events: list[tuple[str, str]]) -> None:
        self.events = events
        self.call_count = 0
        self.final_material = None

    def send_chat(self, model, messages, max_tokens=None):
        self.call_count += 1
        if self.call_count == 1:
            self.events.append(("provider-primary", messages[-1].content))
            return ChatResult("Gemma primary response.", model)
        material = json.loads(messages[-1].content)
        self.final_material = material
        self.events.append(("provider-final", material["primary_response"]))
        return ChatResult("Gemma final corrected response.", model)


def _response_centric_engine():
    events: list[tuple[str, str]] = []
    engine = DemoEngine.__new__(DemoEngine)
    engine._api_key = "test-only"
    engine._provider = _ResponseCentricProvider(events)
    engine._ledger = ProviderCallLedger(maximum_calls=2)
    engine._knowledge = _ResponseCentricKnowledge(events)
    engine._conversation = []
    engine._lock = threading.Lock()
    return engine, events


class GermanLawResponseReviewTests(unittest.TestCase):
    def test_hat_audits_primary_then_returns_brief_to_gemma_final(self) -> None:
        engine, events = _response_centric_engine()
        audit = HatAuditResult(
            verdict="CORRECTION_REQUIRED",
            claims=({"claim": "draft", "status": "INCORRECT"},),
            corrections=(
                {
                    "exact_point": "wrong duty basis",
                    "corrected_proposition": "Use §2 NachwG.",
                    "statutory_basis": ["§2 NachwG"],
                    "knowledge_ids": ["DE-NACHWG-DUTY-2022-001"],
                },
            ),
            missing_information=(),
            temporal_context={"scenario_date": "2026-07-22"},
            finalization_instructions=("Correct the duty basis.",),
            evidence_ids=("DE-NACHWG-DUTY-2022-001",),
        )

        def fake_audit(**kwargs):
            events.append(("hat-audit", kwargs["primary_response"]))
            return audit

        def fake_postcheck(**kwargs):
            events.append(("final-postcheck", kwargs["final_response"]))
            return True

        with patch(
            "apps.aoia_desktop_demo.recording_web.runtime.audit_response",
            side_effect=fake_audit,
        ), patch(
            "apps.aoia_desktop_demo.recording_web.runtime.postcheck_final",
            side_effect=fake_postcheck,
        ):
            result = engine._run_knowledge(
                "run-test",
                "A normal conversational German-law question, not a preset.",
                DEFAULT_MODEL_ID,
                lambda *_args: None,
            )
        self.assertEqual(
            [event[0] for event in events],
            [
                "provider-primary",
                "retrieval",
                "hat-audit",
                "provider-final",
                "final-postcheck",
            ],
        )
        self.assertEqual(events[1][1], "Gemma primary response.")
        self.assertEqual(events[2][1], "Gemma primary response.")
        self.assertEqual(events[3][1], "Gemma primary response.")
        self.assertEqual(result["answer"], "Gemma final corrected response.")
        self.assertEqual(result["classification"], "CORRECTION_REQUIRED")
        self.assertEqual(result["provider_calls"], 2)
        self.assertEqual(result["audit_summary"]["step18_count"], 36)
        self.assertEqual(
            engine._provider.final_material["mandatory_final_check"][
                "contract_status"
            ],
            "VALID",
        )

    def test_failed_final_postcheck_fails_closed(self) -> None:
        engine, _events = _response_centric_engine()
        audit = HatAuditResult(
            verdict="PASS",
            claims=(),
            corrections=(),
            missing_information=(),
            temporal_context={"scenario_date": "2026-07-22"},
            finalization_instructions=(),
            evidence_ids=("DE-NACHWG-DUTY-2022-001",),
        )
        with patch(
            "apps.aoia_desktop_demo.recording_web.runtime.audit_response",
            return_value=audit,
        ), patch(
            "apps.aoia_desktop_demo.recording_web.runtime.postcheck_final",
            return_value=False,
        ):
            with self.assertRaisesRegex(
                DemoRuntimeError,
                "FINAL_RESPONSE_VERIFICATION_FAILED",
            ):
                engine._run_knowledge(
                    "run-test",
                    "German-law question",
                    DEFAULT_MODEL_ID,
                    lambda *_args: None,
                )


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
        self.assertIn("Primary · UNVERIFIED", script)
        self.assertIn("Final · ${result.verified ? \"VERIFIED\" : \"LIMITED\"}", script)
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
