from __future__ import annotations

import unittest

from retrieval.linux import LinuxRetrievalEngine


class ProvenanceAttachmentTests(unittest.TestCase):
    def test_all_answered_results_include_provenance_payload(self) -> None:
        response = LinuxRetrievalEngine(max_results=5).retrieve("ls")

        self.assertTrue(response.answered)
        self.assertTrue(response.results)
        for result in response.results:
            provenance = result.get("provenance")
            self.assertIsInstance(provenance, dict)
            self.assertIn("source_file", provenance)
            self.assertIn("source_page", provenance)
            self.assertIn("canonical_source", provenance)
            self.assertIn("confidence_score", provenance)
            self.assertEqual(provenance["confidence_score"], response.confidence_score)


if __name__ == "__main__":
    unittest.main()

