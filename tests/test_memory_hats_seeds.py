import ast
import importlib
import inspect
import re
import unittest

from runtime.memory_hats import (
    LINUX_RHCSA_SEED_TAGS_PATH,
    PheromoneTag,
    ReviewStatus,
    SQLiteTagStore,
    TagType,
    import_seed_tags_into_store,
    is_valid_leaf_path,
    load_linux_rhcsa_seed_tags,
    lookup_advisory_for_command,
)


class MemoryHatsSeedTests(unittest.TestCase):
    def setUp(self):
        self.store = SQLiteTagStore(":memory:")

    def tearDown(self):
        self.store.close()

    def test_seed_jsonl_file_exists_at_expected_path(self):
        self.assertTrue(LINUX_RHCSA_SEED_TAGS_PATH.exists())
        self.assertEqual("linux_rhcsa_seed_tags.jsonl", LINUX_RHCSA_SEED_TAGS_PATH.name)

    def test_load_linux_rhcsa_seed_tags_returns_tiny_seed_set(self):
        tags = load_linux_rhcsa_seed_tags()

        self.assertGreaterEqual(len(tags), 3)
        self.assertLessEqual(len(tags), 7)

    def test_all_seed_tags_are_pheromone_tags(self):
        tags = load_linux_rhcsa_seed_tags()

        self.assertTrue(all(isinstance(tag, PheromoneTag) for tag in tags))

    def test_all_seed_tags_use_linux_rhcsa_hat(self):
        tags = load_linux_rhcsa_seed_tags()

        self.assertTrue(all(tag.hat_id == "linux_rhcsa" for tag in tags))

    def test_all_seed_tags_have_valid_non_empty_fingerprint_hash(self):
        tags = load_linux_rhcsa_seed_tags()
        sha256_pattern = re.compile(r"^[0-9a-f]{64}$")

        self.assertTrue(
            all(sha256_pattern.fullmatch(tag.fingerprint_hash) for tag in tags)
        )

    def test_all_seed_tags_have_valid_leaf_vein_paths(self):
        tags = load_linux_rhcsa_seed_tags()

        self.assertTrue(all(is_valid_leaf_path(tag.path) for tag in tags))

    def test_seed_tags_use_candidate_or_confirmed_status_only(self):
        tags = load_linux_rhcsa_seed_tags()
        allowed = {ReviewStatus.CANDIDATE, ReviewStatus.CONFIRMED}

        self.assertTrue(all(tag.review_status in allowed for tag in tags))
        self.assertTrue(all(tag.review_status != ReviewStatus.REJECTED for tag in tags))

    def test_required_dnf_status_sshd_seed_tag_exists(self):
        tags = load_linux_rhcsa_seed_tags()
        matches = [tag for tag in tags if tag.normalized_trigger == "dnf status sshd"]

        self.assertEqual(1, len(matches))
        self.assertEqual(ReviewStatus.CONFIRMED, matches[0].review_status)
        self.assertEqual(
            "linux_rhcsa/command_grammar/unsupported_linux_command/dnf_status_sshd",
            matches[0].path,
        )

    def test_dnf_status_seed_returns_high_confidence_advisory_after_import(self):
        tags = load_linux_rhcsa_seed_tags()
        import_seed_tags_into_store(self.store, tags)

        warning = lookup_advisory_for_command("dnf status sshd", self.store)

        self.assertIsNotNone(warning)
        self.assertTrue(warning.active)
        self.assertEqual("high", warning.confidence)
        self.assertEqual("dnf status sshd", warning.normalized_trigger)

    def test_import_seed_tags_into_store_is_idempotent(self):
        tags = load_linux_rhcsa_seed_tags()

        first_count = import_seed_tags_into_store(self.store, tags)
        second_count = import_seed_tags_into_store(self.store, tags)
        stored = self.store.list_by_hat("linux_rhcsa")

        self.assertEqual(len(tags), first_count)
        self.assertEqual(len(tags), second_count)
        self.assertEqual(len(tags), len(stored))

    def test_seed_import_does_not_mutate_seen_count_unexpectedly(self):
        tags = load_linux_rhcsa_seed_tags()
        target = next(tag for tag in tags if tag.normalized_trigger == "dnf status sshd")

        import_seed_tags_into_store(self.store, tags)
        import_seed_tags_into_store(self.store, tags)
        restored = self.store.get_by_fingerprint(target.fingerprint_hash)

        self.assertIsNotNone(restored)
        self.assertEqual(1, target.seen_count)
        self.assertEqual(1, restored.seen_count)

    def test_archive_pipeline_advisory_seed_is_discoverable_and_safe_text_only(self):
        tags = load_linux_rhcsa_seed_tags()
        import_seed_tags_into_store(self.store, tags)

        warning = lookup_advisory_for_command(
            "tar archive from find print0 command substitution",
            self.store,
            tag_type=TagType.COMMAND_SHAPE_SUSPICIOUS,
            secondary_vein="command_shape_suspicious",
        )

        self.assertIsNotNone(warning)
        self.assertTrue(warning.active)
        self.assertEqual("low", warning.confidence)
        self.assertIn("dry-run", warning.correction_text)
        self.assertIn("find", warning.correction_text)
        self.assertIn("-xdev", warning.correction_text)
        self.assertIn("-print0", warning.correction_text)
        self.assertIn("tar --null", warning.correction_text)
        self.assertIn("--files-from=-", warning.correction_text)
        self.assertIn("tar -tzf", warning.correction_text)
        self.assertIn("rm -rf $(find ...)", warning.correction_text)
        self.assertNotIn("tar -czvf ~/aoia_test_lab/archive/logs.tar.gz $(find", warning.correction_text)
        self.assertNotIn("archive was created", warning.correction_text.lower())

    def test_seed_module_has_no_forbidden_imports(self):
        module = importlib.import_module("runtime.memory_hats.seeds")
        source = inspect.getsource(module)
        tree = ast.parse(source)
        imported_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_names.add(node.module)

        forbidden_imports = {
            "subprocess",
            "socket",
            "http.client",
            "urllib",
            "urllib.request",
            "requests",
            "httpx",
            "runtime.tools.command_grammar",
            "runtime.commands",
            "runtime.router",
            "runtime.providers",
        }
        self.assertTrue(forbidden_imports.isdisjoint(imported_names))
        self.assertNotIn("os.system", source)
        self.assertNotIn("subprocess.", source)


if __name__ == "__main__":
    unittest.main()
