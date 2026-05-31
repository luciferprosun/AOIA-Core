import ast
import importlib
import inspect
import unittest

from runtime.memory_hats import (
    build_leaf_path,
    is_valid_leaf_path,
    parent_leaf_path,
    parse_leaf_path,
    path_matches_prefix,
    slugify_path_component,
)


class MemoryHatsLeafRouteTests(unittest.TestCase):
    def test_slugify_path_component_lowercases(self):
        self.assertEqual("command", slugify_path_component("COMMAND"))

    def test_slugify_path_component_strips_whitespace(self):
        self.assertEqual("unsupported_command", slugify_path_component("  Unsupported Command  "))

    def test_slugify_path_component_converts_spaces_to_underscores(self):
        self.assertEqual("dnf_status_sshd", slugify_path_component("dnf status sshd"))

    def test_slugify_path_component_handles_punctuation_deterministically(self):
        self.assertEqual("a_b_c", slugify_path_component("A/B:C"))

    def test_slugify_path_component_collapses_repeated_underscores(self):
        self.assertEqual("a_b", slugify_path_component("a///b"))

    def test_slugify_path_component_rejects_non_string(self):
        with self.assertRaises(TypeError):
            slugify_path_component(None)  # type: ignore[arg-type]

    def test_build_leaf_path_creates_expected_path(self):
        self.assertEqual(
            "linux_rhcsa/command_grammar/unsupported_command/dnf_status_sshd",
            build_leaf_path(
                "linux_rhcsa",
                "Command Grammar",
                "Unsupported Command",
                "dnf status sshd",
            ),
        )

    def test_build_leaf_path_rejects_empty_component_after_slugify(self):
        with self.assertRaises(ValueError):
            build_leaf_path("linux_rhcsa", "command_grammar", "!!!", "dnf status sshd")

    def test_parse_leaf_path_round_trips_build_leaf_path_output(self):
        path = build_leaf_path(
            "linux_rhcsa",
            "command_grammar",
            "unsupported_command",
            "dnf_status_sshd",
        )

        self.assertEqual(
            {
                "hat_id": "linux_rhcsa",
                "primary_vein": "command_grammar",
                "secondary_vein": "unsupported_command",
                "micro_vein": "dnf_status_sshd",
            },
            parse_leaf_path(path),
        )

    def test_parse_leaf_path_rejects_leading_slash(self):
        with self.assertRaises(ValueError):
            parse_leaf_path("/linux_rhcsa/command_grammar/unsupported_command/dnf_status_sshd")

    def test_parse_leaf_path_rejects_too_few_or_many_components(self):
        with self.assertRaises(ValueError):
            parse_leaf_path("linux_rhcsa/command_grammar/unsupported_command")
        with self.assertRaises(ValueError):
            parse_leaf_path("linux_rhcsa/command_grammar/unsupported_command/dnf/status")

    def test_parent_leaf_path_returns_first_three_components(self):
        self.assertEqual(
            "linux_rhcsa/command_grammar/unsupported_command",
            parent_leaf_path(
                "linux_rhcsa/command_grammar/unsupported_command/dnf_status_sshd"
            ),
        )

    def test_is_valid_leaf_path_returns_true_or_false(self):
        self.assertTrue(
            is_valid_leaf_path(
                "linux_rhcsa/command_grammar/unsupported_command/dnf_status_sshd"
            )
        )
        self.assertFalse(is_valid_leaf_path("/linux_rhcsa/command_grammar"))

    def test_path_matches_prefix_uses_segment_prefixes(self):
        path = "linux_rhcsa/command_grammar/unsupported_command/dnf_status_sshd"

        self.assertTrue(path_matches_prefix(path, "linux_rhcsa/command_grammar"))
        self.assertFalse(path_matches_prefix(path, "linux"))

    def test_no_storage_sqlite_rhcsa_or_process_imports(self):
        module = importlib.import_module("runtime.memory_hats.leaf_routes")
        source = inspect.getsource(module)
        tree = ast.parse(source)
        imported_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_names.add(node.module)

        self.assertEqual({"__future__", "re"}, imported_names)
        forbidden_imports = {
            "sqlite3",
            "subprocess",
            "os",
            "pathlib",
            "runtime.tools.command_grammar",
            "runtime.memory",
            "runtime.router",
            "runtime.providers",
            "runtime.knowledge",
        }
        self.assertTrue(forbidden_imports.isdisjoint(imported_names))


if __name__ == "__main__":
    unittest.main()
