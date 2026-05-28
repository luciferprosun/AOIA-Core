from __future__ import annotations

import unittest

from retrieval.linux import LinuxRetrievalEngine


class LinuxRetrievalEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = LinuxRetrievalEngine(max_results=5)

    def test_exact_command_retrieval(self) -> None:
        response = self.engine.retrieve("ls")

        self.assertTrue(response.answered)
        self.assertEqual(response.match_type, "exact")
        self.assertEqual(response.confidence, "high")
        self.assertGreaterEqual(response.confidence_score, 90)
        self.assertTrue(any("ls" in item.get("related_commands", []) for item in response.results))

    def test_alias_retrieval(self) -> None:
        response = self.engine.retrieve("firewall")

        self.assertTrue(response.answered)
        self.assertEqual(response.match_type, "alias")
        self.assertGreaterEqual(response.confidence_score, 90)
        self.assertTrue(response.results)

    def test_subcommand_retrieval(self) -> None:
        response = self.engine.retrieve("systemctl status")

        self.assertTrue(response.answered)
        self.assertIn(response.match_type, {"exact", "subcommand"})
        self.assertGreaterEqual(response.confidence_score, 80)

    def test_invalid_command_refuses(self) -> None:
        response = self.engine.retrieve("zzzz-not-a-linux-command-xyz")

        self.assertFalse(response.answered)
        self.assertEqual(response.status, "refused")
        self.assertEqual(response.confidence, "none")
        self.assertFalse(response.results)
        self.assertIn("clarify", response.message.lower())

    def test_low_confidence_generic_query_refuses(self) -> None:
        response = self.engine.retrieve("linux command")

        self.assertFalse(response.answered)
        self.assertEqual(response.status, "refused")
        self.assertEqual(response.confidence_score, 0)

    def test_provenance_attachment(self) -> None:
        response = self.engine.retrieve("ls")

        self.assertTrue(response.results)
        provenance = response.results[0]["provenance"]
        self.assertIn("source_file", provenance)
        self.assertIn("source_page", provenance)
        self.assertIn("canonical_source", provenance)
        self.assertIn("confidence_score", provenance)
        self.assertEqual(provenance["confidence_score"], response.confidence_score)
        self.assertTrue(provenance["canonical_source"].endswith("linux_master_library_v1.pdf"))

    def test_duplicate_handling(self) -> None:
        response = self.engine.retrieve("ls")

        keys = [
            (
                item.get("file_location"),
                item.get("source_file"),
                item.get("topic"),
                item.get("summary"),
            )
            for item in response.results
        ]
        self.assertEqual(len(keys), len(set(keys)))


if __name__ == "__main__":
    unittest.main()
