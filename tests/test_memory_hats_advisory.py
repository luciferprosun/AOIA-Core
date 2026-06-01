import ast
import importlib
import inspect
import unittest

from runtime.memory_hats import (
    AdvisoryWarning,
    PheromoneTag,
    ReviewStatus,
    TagType,
    advisory_from_tag,
)


class MemoryHatsAdvisoryTests(unittest.TestCase):
    def _tag(self, review_status: ReviewStatus) -> PheromoneTag:
        return PheromoneTag(
            fingerprint_hash="sha256-placeholder",
            hat_id="linux_rhcsa",
            path="linux_rhcsa/command_grammar/unsupported_command/dnf_status_sshd",
            tag_type=TagType.UNSUPPORTED_LINUX_COMMAND,
            normalized_trigger="dnf status sshd",
            correction_text="dnf status is not a supported package query shape.",
            evidence_refs=["evidence://local/ref"],
            review_status=review_status,
            first_seen="2026-06-01T00:00:00Z",
            last_seen="2026-06-01T00:00:00Z",
        )

    def test_advisory_warning_can_be_instantiated(self):
        warning = AdvisoryWarning(
            tag_fingerprint="sha256-placeholder",
            hat_id="linux_rhcsa",
            tag_type="unsupported_linux_command",
            normalized_trigger="dnf status sshd",
            correction_text="Use a supported command shape.",
            evidence_refs=["evidence://local/ref"],
            review_status="candidate",
            confidence="low",
            active=True,
        )

        self.assertEqual("linux_rhcsa", warning.hat_id)
        self.assertTrue(warning.active)

    def test_to_dict_returns_expected_keys(self):
        warning = advisory_from_tag(self._tag(ReviewStatus.CANDIDATE))

        self.assertIsNotNone(warning)
        self.assertEqual(
            {
                "tag_fingerprint",
                "hat_id",
                "tag_type",
                "normalized_trigger",
                "correction_text",
                "evidence_refs",
                "review_status",
                "confidence",
                "active",
                "reason",
            },
            set(warning.to_dict()),
        )

    def test_confirmed_tag_creates_active_high_confidence_advisory(self):
        warning = advisory_from_tag(self._tag(ReviewStatus.CONFIRMED))

        self.assertIsNotNone(warning)
        self.assertTrue(warning.active)
        self.assertEqual("high", warning.confidence)
        self.assertEqual("confirmed", warning.review_status)

    def test_candidate_tag_creates_active_low_confidence_advisory(self):
        warning = advisory_from_tag(self._tag(ReviewStatus.CANDIDATE))

        self.assertIsNotNone(warning)
        self.assertTrue(warning.active)
        self.assertEqual("low", warning.confidence)
        self.assertEqual("candidate", warning.review_status)

    def test_rejected_tag_returns_none(self):
        self.assertIsNone(advisory_from_tag(self._tag(ReviewStatus.REJECTED)))

    def test_advisory_from_tag_does_not_mutate_original_tag(self):
        tag = self._tag(ReviewStatus.CONFIRMED)
        before = tag.to_dict()

        advisory_from_tag(tag)

        self.assertEqual(before, tag.to_dict())

    def test_evidence_refs_are_copied_not_shared(self):
        tag = self._tag(ReviewStatus.CONFIRMED)
        warning = advisory_from_tag(tag)

        self.assertIsNotNone(warning)
        warning.evidence_refs.append("evidence://local/second")

        self.assertEqual(["evidence://local/ref"], tag.evidence_refs)

    def test_no_storage_sqlite_rhcsa_or_process_imports(self):
        module = importlib.import_module("runtime.memory_hats.advisory")
        source = inspect.getsource(module)
        tree = ast.parse(source)
        imported_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_names.add(node.module)

        forbidden_imports = {
            "sqlite3",
            "subprocess",
            "runtime.memory_hats.storage",
            "runtime.tools.command_grammar",
            "runtime.memory",
            "runtime.router",
            "runtime.providers",
            "runtime.knowledge",
        }
        self.assertTrue(forbidden_imports.isdisjoint(imported_names))


if __name__ == "__main__":
    unittest.main()
