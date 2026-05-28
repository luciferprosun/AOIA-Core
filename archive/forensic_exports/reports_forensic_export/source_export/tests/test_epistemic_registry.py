import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools import epistemic_registry


class EpistemicRegistryTests(unittest.TestCase):
    def test_detect_self_references_flags_self_edge(self) -> None:
        graph = {"knowledge/a.md": ["knowledge/a.md"]}
        findings = epistemic_registry.detect_self_references(graph)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["type"], "self_reference")

    def test_detect_circular_references_finds_simple_cycle(self) -> None:
        graph = {
            "knowledge/a.md": ["knowledge/b.md"],
            "knowledge/b.md": ["knowledge/a.md"],
        }
        findings = epistemic_registry.detect_circular_references(graph)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["type"], "circular_reference")

    def test_duplicate_command_detection_finds_multiple_sources(self) -> None:
        artifacts = (
            epistemic_registry.KnowledgeArtifact(
                path=Path("/repo/knowledge/a.md"),
                artifact_type="markdown",
                metadata={},
                references=(),
                commands=("ls",),
                content_hash="hash-a",
            ),
            epistemic_registry.KnowledgeArtifact(
                path=Path("/repo/knowledge/b.md"),
                artifact_type="markdown",
                metadata={},
                references=(),
                commands=("ls",),
                content_hash="hash-b",
            ),
        )
        findings = epistemic_registry.detect_duplicate_commands(artifacts)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["command"], "ls")

    def test_duplicate_artifact_detection_uses_hash(self) -> None:
        artifacts = (
            epistemic_registry.KnowledgeArtifact(
                path=Path("/repo/knowledge/a.md"),
                artifact_type="markdown",
                metadata={},
                references=(),
                commands=(),
                content_hash="same-hash",
            ),
            epistemic_registry.KnowledgeArtifact(
                path=Path("/repo/knowledge/b.md"),
                artifact_type="markdown",
                metadata={},
                references=(),
                commands=(),
                content_hash="same-hash",
            ),
        )
        findings = epistemic_registry.detect_duplicate_artifacts(artifacts)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["type"], "duplicate_content")

    def test_write_registries_writes_json_files(self) -> None:
        with TemporaryDirectory() as tmp:
            provenance_path = Path(tmp) / "provenance_registry.json"
            contradiction_path = Path(tmp) / "contradiction_registry.json"
            provenance, contradictions = epistemic_registry.write_registries(
                provenance_path=provenance_path,
                contradiction_path=contradiction_path,
            )
            self.assertTrue(provenance_path.exists())
            self.assertTrue(contradiction_path.exists())
            self.assertIn("artifact_count", provenance)
            self.assertIn("summary", contradictions)


if __name__ == "__main__":
    unittest.main()
