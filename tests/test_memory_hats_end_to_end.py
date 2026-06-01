import ast
import importlib
import inspect
import unittest

from runtime.memory_hats import (
    ReviewStatus,
    SQLiteTagStore,
    import_seed_tags_into_store,
    load_linux_rhcsa_seed_tags,
    lookup_advisory_for_command,
)


class TestMemoryHatsEndToEndPrototype(unittest.TestCase):
    def setUp(self):
        self.store = SQLiteTagStore(":memory:")

    def tearDown(self):
        self.store.close()

    def _load_and_import_seed_tags(self):
        tags = load_linux_rhcsa_seed_tags()
        import_seed_tags_into_store(self.store, tags)
        return tags

    def test_seed_to_store_to_advisory_warning(self):
        self._load_and_import_seed_tags()

        warning = lookup_advisory_for_command("dnf status sshd", self.store)

        self.assertIsNotNone(warning)
        self.assertTrue(warning.active)
        self.assertEqual("high", warning.confidence)
        self.assertEqual("linux_rhcsa", warning.hat_id)
        self.assertEqual("dnf status sshd", warning.normalized_trigger)
        self.assertIn("systemctl status sshd", warning.correction_text)
        self.assertIn("dnf", warning.correction_text)

    def test_missing_command_returns_none(self):
        self._load_and_import_seed_tags()

        warning = lookup_advisory_for_command(
            "dnf imaginary-subcommand sshd",
            self.store,
        )

        self.assertIsNone(warning)

    def test_candidate_seed_returns_low_confidence_if_present(self):
        tags = self._load_and_import_seed_tags()
        candidate = next(
            (tag for tag in tags if tag.review_status == ReviewStatus.CANDIDATE),
            None,
        )
        if candidate is None:
            self.skipTest("seed set does not include a candidate tag")

        warning = lookup_advisory_for_command(
            candidate.normalized_trigger,
            self.store,
        )

        self.assertIsNotNone(warning)
        self.assertTrue(warning.active)
        self.assertEqual("low", warning.confidence)
        self.assertEqual(candidate.normalized_trigger, warning.normalized_trigger)

    def test_repeated_seed_import_is_idempotent_for_lookup(self):
        tags = load_linux_rhcsa_seed_tags()

        first_count = import_seed_tags_into_store(self.store, tags)
        second_count = import_seed_tags_into_store(self.store, tags)
        stored_tags = self.store.list_by_hat("linux_rhcsa")
        warning = lookup_advisory_for_command("dnf status sshd", self.store)

        self.assertEqual(len(tags), first_count)
        self.assertEqual(len(tags), second_count)
        self.assertEqual(len(tags), len(stored_tags))
        self.assertIsNotNone(warning)
        self.assertEqual("high", warning.confidence)

    def test_end_to_end_does_not_mutate_seen_count(self):
        tags = self._load_and_import_seed_tags()
        target = next(tag for tag in tags if tag.normalized_trigger == "dnf status sshd")
        before = self.store.get_by_fingerprint(target.fingerprint_hash)

        self.assertIsNotNone(before)
        lookup_advisory_for_command("dnf status sshd", self.store)
        after = self.store.get_by_fingerprint(target.fingerprint_hash)

        self.assertIsNotNone(after)
        self.assertEqual(before.seen_count, after.seen_count)

    def test_no_command_execution_imports(self):
        modules = [
            importlib.import_module("runtime.memory_hats.rhcsa_integration"),
            importlib.import_module("runtime.memory_hats.seeds"),
            importlib.import_module("runtime.memory_hats.jsonl"),
        ]

        for module in modules:
            source = inspect.getsource(module)
            tree = ast.parse(source)
            imported_names = _imported_module_names(tree)

            forbidden_imports = {
                "os",
                "subprocess",
                "runtime.tools.command_grammar",
            }
            self.assertTrue(forbidden_imports.isdisjoint(imported_names))
            self.assertNotIn("os.system", source)
            self.assertNotIn("subprocess.", source)
            self.assertNotIn(".popen", source)
            self.assertNotIn("Popen", source)

    def test_end_to_end_components_do_not_require_runtime_integration(self):
        modules = [
            importlib.import_module("runtime.memory_hats.rhcsa_integration"),
            importlib.import_module("runtime.memory_hats.seeds"),
            importlib.import_module("runtime.memory_hats.jsonl"),
        ]
        forbidden_prefixes = (
            "runtime.commands",
            "runtime.router",
            "runtime.providers",
            "runtime.orchestrator",
            "runtime.provenance",
            "runtime.web",
            "runtime.tui",
            "runtime.tools.command_grammar",
        )

        for module in modules:
            tree = ast.parse(inspect.getsource(module))
            imported_names = _imported_module_names(tree)

            self.assertFalse(
                any(
                    imported_name.startswith(forbidden_prefixes)
                    for imported_name in imported_names
                )
            )


def _imported_module_names(tree: ast.AST) -> set[str]:
    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module)
    return imported_names


if __name__ == "__main__":
    unittest.main()
