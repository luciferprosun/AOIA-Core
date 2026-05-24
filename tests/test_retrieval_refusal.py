from __future__ import annotations

import unittest

from adaptive_routing.epistemic_kernel import AOIAEpistemicKernel
from knowledge.rhcsa_engine import RHCSAKnowledgeEngine
from retrieval.linux import LinuxRetrievalEngine


class RetrievalRefusalTests(unittest.TestCase):
    def test_engine_refuses_unresolved_query(self) -> None:
        response = LinuxRetrievalEngine(max_results=5).retrieve("zzzz-not-a-linux-command-xyz")

        self.assertFalse(response.answered)
        self.assertEqual(response.status, "refused")
        self.assertEqual(response.confidence, "none")
        self.assertEqual(response.results, ())

    def test_legacy_facade_preserves_refusal_score(self) -> None:
        hit = RHCSAKnowledgeEngine(project_dir=None).retrieve_operational_memory("zzzz-not-a-linux-command-xyz")

        self.assertFalse(hit.has_operational_memory)
        self.assertEqual(hit.confidence, "none")
        self.assertEqual(hit.score, 0)

    def test_kernel_does_not_route_without_local_evidence(self) -> None:
        decision = AOIAEpistemicKernel(project_dir=None).evaluate("zzzz-not-a-linux-command-xyz")

        self.assertFalse(decision.should_respond_locally)
        self.assertEqual(decision.route, "model_fallback")
        self.assertEqual(decision.confidence, "none")
        self.assertIn("no_local_evidence", decision.manual_review_reasons)


if __name__ == "__main__":
    unittest.main()

