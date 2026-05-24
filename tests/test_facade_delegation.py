from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from knowledge.rhcsa_engine import RHCSAKnowledgeEngine


class FacadeDelegationTests(unittest.TestCase):
    def test_rhcsa_engine_delegates_operational_retrieval_to_facade(self) -> None:
        fake_response = SimpleNamespace(
            results=(
                {
                    "topic": "filesystem",
                    "file_location": "runtime/knowledge/filesystem/example.md",
                    "provenance": {"source_file": "runtime/knowledge/filesystem/example.md"},
                },
            ),
            confidence="high",
            confidence_score=100,
            message="Local Linux/RHCSA retrieval hit.",
        )

        with patch("knowledge.rhcsa_engine.retrieve_linux_knowledge", return_value=fake_response) as fake_retrieve:
            engine = RHCSAKnowledgeEngine(Path("/tmp/aioa-test"))
            hit = engine.retrieve_operational_memory("ls")

        fake_retrieve.assert_called_once_with("ls", project_dir=Path("/tmp/aioa-test"))
        self.assertEqual(hit.confidence, "high")
        self.assertEqual(hit.score, 100)
        self.assertEqual(len(hit.commands), 1)

    def test_rhcsa_engine_is_marked_deprecated(self) -> None:
        self.assertTrue(RHCSAKnowledgeEngine.deprecated)


if __name__ == "__main__":
    unittest.main()
