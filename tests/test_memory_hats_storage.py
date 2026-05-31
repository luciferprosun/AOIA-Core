import ast
import importlib
import inspect
import unittest

from runtime.memory_hats import (
    PheromoneTag,
    ReviewStatus,
    SQLiteTagStore,
    TagType,
    build_leaf_path,
    fingerprint_for_trigger,
    normalize_trigger,
)


class MemoryHatsStorageTests(unittest.TestCase):
    def setUp(self):
        self.store = SQLiteTagStore(":memory:")

    def tearDown(self):
        self.store.close()

    def _tag(
        self,
        trigger: str = "dnf status sshd",
        hat_id: str = "linux_rhcsa",
        review_status: ReviewStatus = ReviewStatus.CANDIDATE,
    ) -> PheromoneTag:
        normalized_trigger = normalize_trigger(trigger)
        path = build_leaf_path(
            hat_id,
            "command_grammar",
            "unsupported_command",
            normalized_trigger,
        )
        return PheromoneTag(
            fingerprint_hash=fingerprint_for_trigger(
                trigger,
                hat_id,
                TagType.UNSUPPORTED_LINUX_COMMAND.value,
            ),
            hat_id=hat_id,
            path=path,
            tag_type=TagType.UNSUPPORTED_LINUX_COMMAND,
            normalized_trigger=normalized_trigger,
            correction_text="Use a supported package query shape.",
            evidence_refs=["evidence://local/ref"],
            review_status=review_status,
            first_seen="2026-06-01T00:00:00Z",
            last_seen="2026-06-01T00:00:00Z",
        )

    def test_store_initializes_in_memory_database(self):
        self.assertIsNone(self.store.get_by_fingerprint("missing"))

    def test_insert_tag_and_get_by_fingerprint_round_trip(self):
        tag = self._tag()

        self.store.insert_tag(tag)

        self.assertEqual(tag, self.store.get_by_fingerprint(tag.fingerprint_hash))

    def test_evidence_refs_round_trip_as_list(self):
        tag = self._tag()
        tag.evidence_refs.append("evidence://local/second")

        self.store.insert_tag(tag)
        restored = self.store.get_by_fingerprint(tag.fingerprint_hash)

        self.assertIsNotNone(restored)
        self.assertEqual(
            ["evidence://local/ref", "evidence://local/second"],
            restored.evidence_refs,
        )

    def test_get_by_fingerprint_returns_none_for_missing_hash(self):
        self.assertIsNone(self.store.get_by_fingerprint("missing"))

    def test_duplicate_insert_is_idempotent(self):
        tag = self._tag()

        first = self.store.insert_tag(tag)
        second = self.store.insert_tag(tag)
        matches = self.store.get_by_path(tag.path)

        self.assertEqual(first, second)
        self.assertEqual(1, len(matches))

    def test_get_by_path_returns_matching_tag_list(self):
        tag = self._tag()
        other = self._tag("systemctl status sshd")

        self.store.insert_tag(tag)
        self.store.insert_tag(other)

        self.assertEqual([tag], self.store.get_by_path(tag.path))

    def test_list_by_hat_returns_only_tags_for_given_hat(self):
        tag = self._tag()
        other = self._tag("dnf status httpd", "linux_general")

        self.store.insert_tag(tag)
        self.store.insert_tag(other)

        self.assertEqual([tag], self.store.list_by_hat("linux_rhcsa"))

    def test_list_by_hat_filters_by_review_status(self):
        candidate = self._tag("dnf status sshd")
        confirmed = self._tag("dnf status httpd", review_status=ReviewStatus.CONFIRMED)

        self.store.insert_tag(candidate)
        self.store.insert_tag(confirmed)

        self.assertEqual(
            [confirmed],
            self.store.list_by_hat("linux_rhcsa", ReviewStatus.CONFIRMED.value),
        )

    def test_update_review_status_changes_candidate_to_confirmed(self):
        tag = self._tag()
        self.store.insert_tag(tag)

        updated = self.store.update_review_status(
            tag.fingerprint_hash,
            ReviewStatus.CONFIRMED,
        )
        restored = self.store.get_by_fingerprint(tag.fingerprint_hash)

        self.assertTrue(updated)
        self.assertIsNotNone(restored)
        self.assertEqual(ReviewStatus.CONFIRMED, restored.review_status)

    def test_update_review_status_returns_false_for_missing_hash(self):
        self.assertFalse(
            self.store.update_review_status("missing", ReviewStatus.CONFIRMED)
        )

    def test_increment_seen_count_increments_from_one_to_two(self):
        tag = self._tag()
        self.store.insert_tag(tag)

        updated = self.store.increment_seen_count(tag.fingerprint_hash)
        restored = self.store.get_by_fingerprint(tag.fingerprint_hash)

        self.assertTrue(updated)
        self.assertIsNotNone(restored)
        self.assertEqual(2, restored.seen_count)

    def test_increment_seen_count_returns_false_for_missing_hash(self):
        self.assertFalse(self.store.increment_seen_count("missing"))

    def test_independent_tags_do_not_share_evidence_refs_list(self):
        first = self._tag("dnf status sshd")
        second = self._tag("dnf status httpd")
        self.store.insert_tag(first)
        self.store.insert_tag(second)

        restored_first = self.store.get_by_fingerprint(first.fingerprint_hash)
        restored_second = self.store.get_by_fingerprint(second.fingerprint_hash)

        self.assertIsNotNone(restored_first)
        self.assertIsNotNone(restored_second)
        restored_first.evidence_refs.append("evidence://local/mutated")
        self.assertEqual(["evidence://local/ref"], restored_second.evidence_refs)

    def test_no_network_subprocess_rhcsa_or_runtime_integration_imports(self):
        module = importlib.import_module("runtime.memory_hats.storage")
        source = inspect.getsource(module)
        tree = ast.parse(source)
        imported_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_names.add(node.module)

        forbidden_imports = {
            "requests",
            "httpx",
            "socket",
            "subprocess",
            "runtime.tools.command_grammar",
            "runtime.memory",
            "runtime.router",
            "runtime.providers",
            "runtime.knowledge",
        }
        self.assertTrue(forbidden_imports.isdisjoint(imported_names))


if __name__ == "__main__":
    unittest.main()
