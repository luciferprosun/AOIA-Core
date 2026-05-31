import inspect
import unittest

from runtime.tools import command_grammar
from runtime.tools.command_grammar import validate_command_shape


class CommandGrammarTests(unittest.TestCase):
    def assert_required_shape(self, result):
        self.assertIsInstance(result, dict)
        self.assertEqual(
            {
                "status",
                "family",
                "base",
                "confidence",
                "danger",
                "reasons",
                "matched_pattern_id",
            },
            set(result),
        )

    def test_valid_common_shapes(self):
        cases = [
            ("systemctl status sshd", "systemctl"),
            ("systemctl restart httpd", "systemctl"),
            ("dnf install httpd", "dnf"),
            ("dnf search nginx", "dnf"),
            ("firewall-cmd --list-all", "firewall-cmd"),
            ("semanage port -l", "semanage"),
            ("chmod 640 /etc/example.conf", "chmod"),
            ("podman ps", "podman"),
        ]
        for command, base in cases:
            with self.subTest(command=command):
                result = validate_command_shape(command)
                self.assert_required_shape(result)
                self.assertEqual(base, result["base"])
                self.assertIn(result["status"], {"family", "exact"})
                self.assertNotEqual("grammar_reject", result["confidence"])

    def test_suspicious_or_rejected_shapes(self):
        cases = [
            ("systemctl install nginx", "suspicious"),
            ("dnf status httpd", "suspicious"),
            ("journalctl restart sshd", "suspicious"),
            ("chmod user file", "suspicious"),
            ("/etc/passwd", "reject"),
            ("--reload", "reject"),
            ("$PATH", "reject"),
            ("*.log", "reject"),
            ("systemctl status 'unterminated", "reject"),
        ]
        for command, status in cases:
            with self.subTest(command=command):
                result = validate_command_shape(command)
                self.assert_required_shape(result)
                self.assertEqual(status, result["status"])

    def test_unknown_base_is_not_exact(self):
        result = validate_command_shape("journalctl restart sshd")
        self.assert_required_shape(result)
        self.assertIn(result["status"], {"suspicious", "reject"})
        self.assertNotEqual("exact", result["status"])

    def test_pipeline_is_suspicious(self):
        result = validate_command_shape("systemctl status sshd | grep Active")
        self.assert_required_shape(result)
        self.assertEqual("suspicious", result["status"])
        self.assertIn("shell_composition_present", result["reasons"])

    def test_parser_never_executes_commands(self):
        source = inspect.getsource(command_grammar)
        forbidden = ["subprocess", "os.system", "Popen", "run(", "exec("]
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_module_documents_shellcheck_and_tree_sitter_boundary(self):
        doc = command_grammar.__doc__ or ""
        self.assertIn("does not replace ShellCheck", doc)
        self.assertIn("tree-sitter-bash", doc)
        self.assertIn("non-executing", doc)

    def test_no_shellcheck_or_tree_sitter_dependency(self):
        source = inspect.getsource(command_grammar)
        self.assertNotIn("import shellcheck", source.lower())
        self.assertNotIn("tree_sitter", source)
        self.assertNotIn("tree-sitter", source.replace("tree-sitter-bash", "documented-boundary"))


if __name__ == "__main__":
    unittest.main()
