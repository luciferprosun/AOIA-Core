from pathlib import Path
import re
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = REPO_ROOT / "docs" / "ui" / "UI_STATE_CONTRACT.md"
THIS_FILE = Path(__file__).resolve()


class M6CUIFacadeBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract_text = CONTRACT.read_text(encoding="utf-8")

    def assert_contains_all(self, needles):
        missing = [needle for needle in needles if needle not in self.contract_text]
        self.assertEqual([], missing)

    def test_contract_exists_and_names_authoritative_chain(self):
        self.assertTrue(CONTRACT.exists())
        self.assert_contains_all(
            [
                "HumanApprovalReviewPacket",
                "HumanDecisionCapture",
                "ApprovalDecision",
                "durable ApprovalDecision audit handoff",
                "evaluate_pre_artifact_approval_gate",
                "gated durable artifact write result",
            ]
        )

    def test_non_authoritative_concepts_are_limited_to_context(self):
        self.assert_contains_all(
            [
                "provider/model output",
                "UI labels",
                "UI colors",
                "UI badges",
                "metadata tags",
                "knowledge hats",
                "tetrads/geometry",
                "draft text",
                "CPT previews",
            ]
        )
        non_authoritative_section = self.contract_text[
            self.contract_text.index("## 3. Non-authoritative display/context sources") :
            self.contract_text.index("## 4. UI state categories")
        ]
        self.assertIn("must never grant approval", non_authoritative_section)
        self.assertIn("forbidden authority examples", non_authoritative_section)

    def test_required_safe_ui_state_categories_exist(self):
        self.assert_contains_all(
            [
                "DRAFT_ONLY",
                "REVIEW_PACKET_READY",
                "AWAITING_HUMAN_DECISION",
                "HUMAN_REJECTED",
                "HUMAN_APPROVED_NOT_AUDITED",
                "APPROVED_AND_AUDIT_HANDOFF_COMPLETE",
                "PRE_ARTIFACT_GATE_PASSED",
                "ARTIFACT_WRITE_COMPLETE",
                "ARTIFACT_WRITE_BLOCKED",
                "STALE_OR_MISMATCHED_STATE",
                "ERROR_FAIL_CLOSED",
            ]
        )

    def test_forbidden_state_names_exist_and_stay_forbidden(self):
        forbidden_section = self.contract_text[
            self.contract_text.index("## 5. Forbidden UI states") :
            self.contract_text.index("## 6. Display rules")
        ]
        for forbidden_state in [
            "TRUSTED_MODEL",
            "MODEL_APPROVED",
            "TAG_APPROVED",
            "HAT_APPROVED",
            "TETRAD_APPROVED",
            "GEOMETRY_SAFE",
            "CANONICAL_BY_TAG",
            "SAFE_FOR_RUNTIME",
            "NO_HUMAN_REVIEW_NEEDED",
            "AUTO_APPROVED",
            "EXECUTION_READY",
        ]:
            self.assertIn(forbidden_state, forbidden_section)
        self.assertIn("must not define, render, persist, or route", forbidden_section)
        self.assertIn("approval", forbidden_section)
        self.assertIn("write authority", forbidden_section)

    def test_fail_closed_rules_exist(self):
        fail_closed_section = self.contract_text[
            self.contract_text.index("## 7. Fail-closed rules") :
            self.contract_text.index("## 8. Explicit non-goals")
        ]
        for condition in [
            "missing ApprovalDecision",
            "missing HumanDecisionCapture",
            "missing durable audit handoff",
            "mismatched packet hash",
            "mismatched artifact hash",
            "stale UI state",
            "provider output conflict",
            "unknown state enum",
            "legacy/non-durable path",
        ]:
            self.assertIn(condition, fail_closed_section)
        self.assertIn("Fail-closed means no artifact write", fail_closed_section)
        self.assertIn("no provider call", fail_closed_section)

    def test_m6_c_boundary_test_does_not_import_or_call_dangerous_modules(self):
        source = THIS_FILE.read_text(encoding="utf-8")
        forbidden_imports = [
            "subprocess",
            "urllib",
            "socket",
            "webbrowser",
            "playwright",
            "selenium",
            "requests",
            "httpx",
        ]
        for module_name in forbidden_imports:
            self.assertIsNone(
                re.search(rf"^\s*(from|import)\s+{re.escape(module_name)}\b", source, re.MULTILINE)
            )
        self.assertIsNone(re.search(r"\bos\s*\.\s*system\s*\(", source))

    def test_no_m6_c_research_candidate_docs_introduced(self):
        forbidden_docs = [
            REPO_ROOT / "docs" / "research" / "EPISTEMIC_TAGGING_CANDIDATE.md",
            REPO_ROOT / "docs" / "research" / "TETRAHEDRAL_HAT_CELL_CANDIDATE.md",
        ]
        existing = [path for path in forbidden_docs if path.exists()]
        self.assertEqual([], existing)

    def test_no_obvious_new_tag_tetrad_hat_schema_runtime_files_exist(self):
        forbidden_runtime_candidates = [
            REPO_ROOT / "runtime" / "tag_schema.py",
            REPO_ROOT / "runtime" / "tetrad_schema.py",
            REPO_ROOT / "runtime" / "hat_schema.py",
            REPO_ROOT / "runtime" / "epistemic_tagging.py",
            REPO_ROOT / "runtime" / "tetrahedral_hat_cell.py",
            REPO_ROOT / "runtime" / "validators" / "tag_validator.py",
            REPO_ROOT / "runtime" / "validators" / "tetrad_validator.py",
            REPO_ROOT / "runtime" / "validators" / "hat_validator.py",
        ]
        existing = [path for path in forbidden_runtime_candidates if path.exists()]
        self.assertEqual([], existing)


if __name__ == "__main__":
    unittest.main()
