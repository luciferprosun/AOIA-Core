import importlib
import ast
import inspect
import unittest

from runtime.memory_hats import PheromoneTag, ReviewStatus, SafetyLevel, TagType


class MemoryHatsTagTests(unittest.TestCase):
    def _minimal_tag(self) -> PheromoneTag:
        return PheromoneTag(
            fingerprint_hash="sha256-placeholder",
            hat_id="linux_rhcsa",
            path="linux_rhcsa/command_grammar/unsupported_command/dnf_status_sshd",
            tag_type=TagType.UNSUPPORTED_LINUX_COMMAND,
            normalized_trigger="dnf status sshd",
            correction_text="dnf status is not a supported package query shape.",
            first_seen="2026-06-01T00:00:00Z",
            last_seen="2026-06-01T00:00:00Z",
        )

    def test_module_imports_successfully(self):
        module = importlib.import_module("runtime.memory_hats")

        self.assertIs(module.PheromoneTag, PheromoneTag)
        self.assertIs(module.TagType, TagType)
        self.assertIs(module.ReviewStatus, ReviewStatus)

    def test_tag_type_contains_expected_members(self):
        expected = {
            "UNSUPPORTED_CLAIM",
            "IMPLEMENTATION_OVERCLAIM",
            "COMMAND_SHAPE_SUSPICIOUS",
            "UNSUPPORTED_LINUX_COMMAND",
            "STATE_CHANGING_COMMAND_REQUIRES_REVIEW",
            "CONTRADICTS_KNOWN_STATE",
            "CONFIDENCE_EVIDENCE_MISMATCH",
            "MODEL_DISAGREEMENT",
            "POSSIBLE_SECRET_EXPOSURE",
        }

        self.assertEqual(expected, set(TagType.__members__))

    def test_review_status_contains_expected_members(self):
        self.assertEqual(
            {"CANDIDATE", "CONFIRMED", "REJECTED"},
            set(ReviewStatus.__members__),
        )

    def test_safety_level_is_advisory_only(self):
        self.assertEqual({"ADVISORY"}, set(SafetyLevel.__members__))

    def test_pheromone_tag_can_be_instantiated(self):
        tag = self._minimal_tag()

        self.assertEqual("sha256-placeholder", tag.fingerprint_hash)
        self.assertEqual("linux_rhcsa", tag.hat_id)
        self.assertEqual(TagType.UNSUPPORTED_LINUX_COMMAND, tag.tag_type)

    def test_defaults_are_safe(self):
        tag = self._minimal_tag()

        self.assertEqual(ReviewStatus.CANDIDATE, tag.review_status)
        self.assertEqual(1, tag.seen_count)
        self.assertEqual([], tag.evidence_refs)
        self.assertEqual("manual", tag.created_by)

    def test_evidence_refs_default_is_not_shared(self):
        first = self._minimal_tag()
        second = self._minimal_tag()

        first.evidence_refs.append("local-evidence-ref")

        self.assertEqual(["local-evidence-ref"], first.evidence_refs)
        self.assertEqual([], second.evidence_refs)

    def test_to_dict_from_dict_round_trip(self):
        tag = self._minimal_tag()
        tag.evidence_refs.append("evidence://local/ref")
        tag.review_status = ReviewStatus.CONFIRMED
        tag.notes = "reviewed locally"

        restored = PheromoneTag.from_dict(tag.to_dict())

        self.assertEqual(tag, restored)
        self.assertIsInstance(restored.tag_type, TagType)
        self.assertIsInstance(restored.review_status, ReviewStatus)

    def test_no_external_dependencies(self):
        module = importlib.import_module("runtime.memory_hats.tags")
        source = inspect.getsource(module)

        forbidden_imports = (
            "import requests",
            "import httpx",
            "import sqlite3",
            "from sqlite3",
        )
        for forbidden in forbidden_imports:
            self.assertNotIn(forbidden, source)

    def test_no_storage_routing_hash_or_command_grammar_imports(self):
        module = importlib.import_module("runtime.memory_hats.tags")
        source = inspect.getsource(module)
        tree = ast.parse(source)
        imported_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_names.add(node.module)

        forbidden_imports = {
            "hashlib",
            "command_grammar",
            "leaf_routes",
            "storage",
            "runtime.memory",
            "runtime.knowledge",
            "runtime.router",
            "runtime.providers",
        }
        self.assertTrue(forbidden_imports.isdisjoint(imported_names))


if __name__ == "__main__":
    unittest.main()
