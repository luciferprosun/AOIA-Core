from __future__ import annotations

import unittest

from retrieval.linux import LinuxRetrievalEngine
from retrieval.linux.scoring import EXACT_MATCH_SCORE, REFUSAL_THRESHOLD, confidence_for, should_refuse
from tools.rhcsa_search import exact_command_lookup


class ScoringConsistencyTests(unittest.TestCase):
    def test_exact_lookup_uses_canonical_exact_score(self) -> None:
        results = exact_command_lookup("systemctl status", limit=5)

        self.assertTrue(results)
        self.assertTrue(any(item["score"] == EXACT_MATCH_SCORE for item in results))

    def test_engine_exact_score_matches_canonical_thresholds(self) -> None:
        response = LinuxRetrievalEngine(max_results=5).retrieve("systemctl status")

        self.assertTrue(response.answered)
        self.assertEqual(response.confidence_score, EXACT_MATCH_SCORE)
        self.assertEqual(response.confidence, confidence_for(response.confidence_score))

    def test_refusal_threshold_single_source(self) -> None:
        self.assertTrue(should_refuse(REFUSAL_THRESHOLD - 1))
        self.assertFalse(should_refuse(REFUSAL_THRESHOLD))


if __name__ == "__main__":
    unittest.main()

