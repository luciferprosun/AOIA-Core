from __future__ import annotations

import contextlib
import io
import json
import unittest
from pathlib import Path

from runtime.knowledge_modules.cli import main


ROOT = Path(__file__).resolve().parents[1]


class KnowledgeQueryCli1ATests(unittest.TestCase):
    def invoke(self, *arguments):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            status = main(("--repository-root", str(ROOT), *arguments))
        return status, stream.getvalue()

    def test_list_modules_is_local_disabled_and_json_by_default(self):
        status, output = self.invoke("--list-modules")
        self.assertEqual(status, 0)
        payload = json.loads(output)
        self.assertEqual(payload["status"], "MODULES_LISTED")
        self.assertEqual([item["module_id"] for item in payload["modules"]], ["de-law-federal-1a"])
        self.assertFalse(payload["modules"][0]["enabled_by_default"])
        self.assertFalse(payload["can_call_provider"])
        self.assertFalse(payload["can_write"])

    def test_list_modules_supports_bounded_text_output(self):
        status, output = self.invoke("--list-modules", "--format", "text")
        self.assertEqual(status, 0)
        self.assertEqual(output.strip(), "de-law-federal-1a 1a enabled_by_default=false")

    def test_query_requires_explicit_module_and_external_configuration(self):
        status, output = self.invoke(
            "--question",
            "§ 2 NachwG",
            "--retrieval-mode",
            "source-discovery",
        )
        self.assertEqual(status, 2)
        payload = json.loads(output)
        self.assertEqual(payload["status"], "INVALID_MODULE_CONFIGURATION")
        self.assertIn("module", payload["reason"])

    def test_duplicate_selection_and_missing_as_of_fail_closed_before_external_process(self):
        common = (
            "--module-repository",
            "/home/l/AOIA_PRODUCTION/repos/AOIA-German-Law-Knowledge-Pack",
            "--module-data-root",
            "/home/l/AOIA_PRODUCTION/data/german-law-corpus",
            "--expected-module-head",
            "73f444cdad78fa5d66f76216c19dc41f4c0e3b03",
        )
        status, output = self.invoke(
            "--module",
            "de-law-federal-1a",
            "--module",
            "de-law-federal-1a",
            "--question",
            "§ 2 NachwG",
            "--retrieval-mode",
            "source-discovery",
            *common,
        )
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(output)["status"], "DUPLICATE_MODULE_ID")

        status, output = self.invoke(
            "--module",
            "de-law-federal-1a",
            "--question",
            "§ 2 NachwG",
            "--retrieval-mode",
            "verified-as-of",
            *common,
        )
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(output)["status"], "INVALID_KNOWLEDGE_QUERY")


if __name__ == "__main__":
    unittest.main()
