import ast
import importlib
import inspect
import string
import unittest

from runtime.memory_hats import (
    compute_fingerprint,
    fingerprint_for_trigger,
    normalize_trigger,
)
from runtime.memory_hats.dedup import is_sha256_hex


class MemoryHatsDedupTests(unittest.TestCase):
    def test_normalize_trigger_lowercases(self):
        self.assertEqual("dnf status sshd", normalize_trigger("DNF STATUS SSHD"))

    def test_normalize_trigger_strips_whitespace(self):
        self.assertEqual("dnf status sshd", normalize_trigger("  dnf status sshd  "))

    def test_normalize_trigger_collapses_repeated_whitespace(self):
        self.assertEqual(
            "dnf status sshd",
            normalize_trigger("DNF   status   sshd"),
        )

    def test_normalize_trigger_handles_tabs_and_newlines(self):
        self.assertEqual(
            "systemctl status sshd",
            normalize_trigger("\nSystemCtl   STATUS   sshd\t"),
        )

    def test_normalize_trigger_handles_empty_or_blank_strings(self):
        self.assertEqual("", normalize_trigger(""))
        self.assertEqual("", normalize_trigger("   "))

    def test_normalize_trigger_is_idempotent(self):
        value = "\nDNF   STATUS\tsshd  "
        normalized = normalize_trigger(value)

        self.assertEqual(normalized, normalize_trigger(normalized))

    def test_normalize_trigger_rejects_non_string(self):
        with self.assertRaises(TypeError):
            normalize_trigger(None)  # type: ignore[arg-type]

    def test_compute_fingerprint_returns_lowercase_sha256_hex(self):
        fingerprint = compute_fingerprint(
            "dnf status sshd",
            "linux_rhcsa",
            "unsupported_linux_command",
        )

        self.assertTrue(is_sha256_hex(fingerprint))
        self.assertEqual(64, len(fingerprint))
        self.assertTrue(set(fingerprint).issubset(set(string.hexdigits.lower())))

    def test_compute_fingerprint_is_deterministic(self):
        first = compute_fingerprint(
            "dnf status sshd",
            "linux_rhcsa",
            "unsupported_linux_command",
        )
        second = compute_fingerprint(
            "dnf status sshd",
            "linux_rhcsa",
            "unsupported_linux_command",
        )

        self.assertEqual(first, second)

    def test_compute_fingerprint_changes_when_hat_id_changes(self):
        first = compute_fingerprint("dnf status sshd", "linux_rhcsa", "tag")
        second = compute_fingerprint("dnf status sshd", "linux_general", "tag")

        self.assertNotEqual(first, second)

    def test_compute_fingerprint_changes_when_tag_type_changes(self):
        first = compute_fingerprint("dnf status sshd", "linux_rhcsa", "first")
        second = compute_fingerprint("dnf status sshd", "linux_rhcsa", "second")

        self.assertNotEqual(first, second)

    def test_compute_fingerprint_changes_when_trigger_changes(self):
        first = compute_fingerprint("dnf status sshd", "linux_rhcsa", "tag")
        second = compute_fingerprint("dnf search sshd", "linux_rhcsa", "tag")

        self.assertNotEqual(first, second)

    def test_compute_fingerprint_rejects_non_string_args(self):
        with self.assertRaises(TypeError):
            compute_fingerprint("trigger", "hat", None)  # type: ignore[arg-type]

    def test_fingerprint_for_trigger_normalizes_before_hashing(self):
        first = fingerprint_for_trigger(
            "DNF   status sshd",
            "linux_rhcsa",
            "unsupported_linux_command",
        )
        second = fingerprint_for_trigger(
            "dnf status   sshd",
            "linux_rhcsa",
            "unsupported_linux_command",
        )

        self.assertEqual(first, second)

    def test_no_storage_routing_rhcsa_or_process_imports(self):
        module = importlib.import_module("runtime.memory_hats.dedup")
        source = inspect.getsource(module)
        tree = ast.parse(source)
        imported_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_names.add(node.module)

        self.assertEqual({"__future__", "hashlib", "re"}, imported_names)
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
