import ast
import importlib
import inspect
import unittest

from runtime.memory_hats import (
    PheromoneTag,
    ReviewStatus,
    SQLiteTagStore,
    TagType,
    command_to_memory_hat_path,
    fingerprint_for_trigger,
    lookup_advisory_for_command,
    lookup_advisory_for_grammar_result,
    normalize_trigger,
    validate_and_lookup_advisory,
)


class MemoryHatsRHCSAIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.store = SQLiteTagStore(":memory:")

    def tearDown(self):
        self.store.close()

    def _tag(
        self,
        command: str = "dnf status sshd",
        review_status: ReviewStatus = ReviewStatus.CONFIRMED,
        fingerprint_suffix: str = "",
    ) -> PheromoneTag:
        normalized = normalize_trigger(command)
        fingerprint = fingerprint_for_trigger(
            command,
            "linux_rhcsa",
            TagType.UNSUPPORTED_LINUX_COMMAND.value,
        )
        if fingerprint_suffix:
            fingerprint = f"{fingerprint}-{fingerprint_suffix}"
        return PheromoneTag(
            fingerprint_hash=fingerprint,
            hat_id="linux_rhcsa",
            path=command_to_memory_hat_path(command),
            tag_type=TagType.UNSUPPORTED_LINUX_COMMAND,
            normalized_trigger=normalized,
            correction_text="Use systemctl status sshd for service status checks.",
            evidence_refs=["man systemctl", "man dnf"],
            review_status=review_status,
            first_seen="2026-06-01T00:00:00Z",
            last_seen="2026-06-01T00:00:00Z",
        )

    def test_command_to_memory_hat_path_normalizes_and_builds_expected_path(self):
        self.assertEqual(
            "linux_rhcsa/command_grammar/unsupported_linux_command/dnf_status_sshd",
            command_to_memory_hat_path("DNF   status sshd"),
        )

    def test_lookup_returns_high_confidence_advisory_for_confirmed_tag(self):
        self.store.insert_tag(self._tag(review_status=ReviewStatus.CONFIRMED))

        warning = lookup_advisory_for_command("dnf status sshd", self.store)

        self.assertIsNotNone(warning)
        self.assertTrue(warning.active)
        self.assertEqual("high", warning.confidence)

    def test_lookup_returns_low_confidence_advisory_for_candidate_tag(self):
        self.store.insert_tag(self._tag(review_status=ReviewStatus.CANDIDATE))

        warning = lookup_advisory_for_command("dnf status sshd", self.store)

        self.assertIsNotNone(warning)
        self.assertTrue(warning.active)
        self.assertEqual("low", warning.confidence)

    def test_lookup_returns_none_when_no_tag_exists(self):
        self.assertIsNone(lookup_advisory_for_command("dnf status sshd", self.store))

    def test_lookup_ignores_rejected_tag(self):
        self.store.insert_tag(self._tag(review_status=ReviewStatus.REJECTED))

        self.assertIsNone(lookup_advisory_for_command("dnf status sshd", self.store))

    def test_confirmed_tag_is_preferred_over_candidate_for_same_trigger(self):
        candidate = self._tag(
            review_status=ReviewStatus.CANDIDATE,
            fingerprint_suffix="candidate",
        )
        confirmed = self._tag(
            review_status=ReviewStatus.CONFIRMED,
            fingerprint_suffix="confirmed",
        )
        self.store.insert_tag(candidate)
        self.store.insert_tag(confirmed)

        warning = lookup_advisory_for_command("dnf status sshd", self.store)

        self.assertIsNotNone(warning)
        self.assertEqual("high", warning.confidence)
        self.assertEqual(confirmed.fingerprint_hash, warning.tag_fingerprint)

    def test_lookup_does_not_mutate_seen_count(self):
        tag = self._tag()
        self.store.insert_tag(tag)

        lookup_advisory_for_command("dnf status sshd", self.store)
        restored = self.store.get_by_fingerprint(tag.fingerprint_hash)

        self.assertIsNotNone(restored)
        self.assertEqual(1, restored.seen_count)

    def test_lookup_does_not_modify_store_records(self):
        tag = self._tag()
        self.store.insert_tag(tag)
        before = self.store.get_by_fingerprint(tag.fingerprint_hash).to_dict()

        lookup_advisory_for_command("dnf status sshd", self.store)
        after = self.store.get_by_fingerprint(tag.fingerprint_hash).to_dict()

        self.assertEqual(before, after)

    def test_grammar_result_returns_none_for_read_only_safe_shape(self):
        self.store.insert_tag(self._tag())

        warning = lookup_advisory_for_grammar_result(
            "dnf status sshd",
            "family",
            "read_only",
            self.store,
        )

        self.assertIsNone(warning)

    def test_grammar_result_attempts_lookup_for_suspicious_shape(self):
        self.store.insert_tag(self._tag())

        warning = lookup_advisory_for_grammar_result(
            "dnf status sshd",
            "suspicious",
            "unknown",
            self.store,
        )

        self.assertIsNotNone(warning)
        self.assertEqual("high", warning.confidence)

    def test_validate_and_lookup_advisory_works_with_fake_validator(self):
        self.store.insert_tag(self._tag())

        def fake_validator(command: str) -> dict[str, str]:
            return {"status": "suspicious", "danger": "unknown"}

        warning = validate_and_lookup_advisory(
            "dnf status sshd",
            self.store,
            validator=fake_validator,
        )

        self.assertIsNotNone(warning)
        self.assertEqual("high", warning.confidence)

    def test_no_command_execution_imports_or_calls(self):
        module = importlib.import_module("runtime.memory_hats.rhcsa_integration")
        source = inspect.getsource(module)
        tree = ast.parse(source)
        imported_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_names.add(node.module)

        forbidden_imports = {
            "os",
            "subprocess",
            "runtime.tools.command_grammar",
            "runtime.commands",
            "runtime.router",
            "runtime.providers",
            "runtime.knowledge",
        }
        self.assertTrue(forbidden_imports.isdisjoint(imported_names))
        self.assertNotIn("os.system", source)
        self.assertNotIn("subprocess.", source)


if __name__ == "__main__":
    unittest.main()
