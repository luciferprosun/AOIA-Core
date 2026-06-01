import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "knowledge" / "languages" / "python" / "official_docs_crosscheck"


class PythonOfficialDocsCrosscheckDocsTests(unittest.TestCase):
    def test_plan_exists(self):
        self.assertTrue((DOCS_DIR / "OFFICIAL_DOCS_CROSSCHECK_PLAN.md").exists())

    def test_checklist_template_exists(self):
        self.assertTrue((DOCS_DIR / "CROSSCHECK_CHECKLIST_TEMPLATE.md").exists())

    def test_discrepancy_log_exists_and_is_valid_jsonl(self):
        path = DOCS_DIR / "DISCREPANCY_LOG.jsonl"
        self.assertTrue(path.exists())
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertGreaterEqual(len(lines), 1)
        for line in lines:
            json.loads(line)

    def test_first_targets_exists(self):
        self.assertTrue((DOCS_DIR / "FIRST_CROSSCHECK_TARGETS.md").exists())

    def test_plan_contains_required_guardrails(self):
        text = (DOCS_DIR / "OFFICIAL_DOCS_CROSSCHECK_PLAN.md").read_text(encoding="utf-8")
        self.assertIn("imported_reference_unverified", text)
        self.assertIn("external_model_review_unverified", text)
        self.assertIn("official_docs_checked", text)
        self.assertIn("promoted", text)
        self.assertIn("no record becomes promoted during this phase", text)

    def test_target_list_contains_required_targets(self):
        text = (DOCS_DIR / "FIRST_CROSSCHECK_TARGETS.md").read_text(encoding="utf-8")
        self.assertIn("eval", text)
        self.assertIn("exec", text)
        self.assertIn("subprocess.run", text)
        self.assertIn("pickle.load", text)
        self.assertIn("shutil.rmtree", text)
        self.assertIn("PEP 703", text)


if __name__ == "__main__":
    unittest.main()
