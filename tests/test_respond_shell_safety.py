import json
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import main
from tools.validator import inspect_respond_shell_safety


PROMPT_TEMPLATE = "test prompt"


class FakeProvider:
    def __init__(self, output: str) -> None:
        self.output = output
        self.calls = 0

    def generate(self, _prompt: str) -> str:
        self.calls += 1
        return self.output

    def describe(self) -> str:
        return "fake/test-model"


class RespondShellSafetyTests(unittest.TestCase):
    def test_normal_respond_text_passes_unchanged(self) -> None:
        message = "Use journalctl -u sshd to inspect service logs."

        result = inspect_respond_shell_safety(message)

        self.assertTrue(result.safe)
        self.assertEqual(result.severity, "none")
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.matched_patterns, [])
        self.assertEqual(result.sanitized_message, message)

    def test_harmless_command_is_not_overblocked(self) -> None:
        message = "Use tar -tzvf logs.tar.gz to list archive contents."

        result = inspect_respond_shell_safety(message)

        self.assertTrue(result.safe)
        self.assertEqual(result.severity, "none")
        self.assertEqual(result.sanitized_message, message)

    def test_find_print0_command_substitution_is_detected(self) -> None:
        message = 'tar -czvf logs.tar.gz $(find . -type f -name "*.log" -print0)'

        result = inspect_respond_shell_safety(message)

        self.assertFalse(result.safe)
        self.assertEqual(result.severity, "high_risk")
        self.assertIn("find_print0_command_substitution", result.matched_patterns)
        self.assertIn("tar_find_print0_command_substitution", result.matched_patterns)
        self.assertIn("AOIA HIGH-RISK SHELL ADVICE WARNING", result.sanitized_message)
        self.assertIn("AOIA did not execute this command", result.sanitized_message)
        self.assertIn("find -print0", result.sanitized_message)
        self.assertIn("command substitution", result.sanitized_message)
        self.assertIn("tar --null", result.sanitized_message)
        self.assertIn("--files-from=-", result.sanitized_message)

    def test_rm_rf_root_is_detected(self) -> None:
        result = inspect_respond_shell_safety("Never run rm -rf / on a live system.")

        self.assertFalse(result.safe)
        self.assertEqual(result.severity, "high_risk")
        self.assertIn("rm_rf_destructive_target", result.matched_patterns)

    def test_rm_rf_star_is_detected(self) -> None:
        result = inspect_respond_shell_safety("This cleanup uses rm -rf * in the current directory.")

        self.assertFalse(result.safe)
        self.assertEqual(result.severity, "warning")
        self.assertIn("rm_rf_destructive_target", result.matched_patterns)

    def test_mkfs_is_detected(self) -> None:
        result = inspect_respond_shell_safety("The command mkfs.xfs /dev/sdb1 formats a filesystem.")

        self.assertFalse(result.safe)
        self.assertEqual(result.severity, "high_risk")
        self.assertIn("mkfs_filesystem_format", result.matched_patterns)

    def test_dd_if_of_is_detected(self) -> None:
        result = inspect_respond_shell_safety("Clone with dd if=/dev/sda of=/dev/sdb bs=4M.")

        self.assertFalse(result.safe)
        self.assertEqual(result.severity, "high_risk")
        self.assertIn("dd_if_of_raw_copy", result.matched_patterns)

    def test_sudo_destructive_command_is_detected(self) -> None:
        result = inspect_respond_shell_safety("Run sudo rm -rf /tmp/example only after review.")

        self.assertFalse(result.safe)
        self.assertEqual(result.severity, "high_risk")
        self.assertIn("sudo_destructive_command", result.matched_patterns)

    def test_command_substitution_file_listing_is_detected(self) -> None:
        result = inspect_respond_shell_safety("Archive files with tar -cf files.tar $(find . -type f).")

        self.assertFalse(result.safe)
        self.assertEqual(result.severity, "warning")
        self.assertIn("risky_command_substitution", result.matched_patterns)

    def test_destructive_command_substitution_is_high_risk(self) -> None:
        result = inspect_respond_shell_safety("Never use echo $(rm -rf /tmp/example).")

        self.assertFalse(result.safe)
        self.assertEqual(result.severity, "high_risk")
        self.assertIn("risky_command_substitution", result.matched_patterns)

    def test_non_dangerous_examples_are_not_overblocked(self) -> None:
        safe_examples = [
            "find . -type f -name '*.log' -print0 | tar --null --files-from=- -czvf logs.tar.gz",
            "echo $(date)",
            "tar -tzvf logs.tar.gz",
            "ls -la /var/log",
        ]
        for message in safe_examples:
            with self.subTest(message=message):
                result = inspect_respond_shell_safety(message)
                self.assertTrue(result.safe)
                self.assertEqual(result.severity, "none")
                self.assertEqual(result.sanitized_message, message)

    def test_provider_respond_output_is_warned_before_display(self) -> None:
        unsafe = 'tar -czvf logs.tar.gz $(find . -type f -name "*.log" -print0)'
        payload = json.dumps({"action": "respond", "message": unsafe, "reason": "test"})

        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            runtime = main.AgentRuntime(FakeProvider(payload), PROMPT_TEMPLATE, project_dir)

            with patch("sys.stdout", new_callable=StringIO) as fake_stdout:
                runtime.handle_user_request("show me archive command")

        output = fake_stdout.getvalue()
        self.assertIn("AOIA HIGH-RISK SHELL ADVICE WARNING", output)
        self.assertIn("AOIA did not execute this command", output)
        self.assertIn("find -print0", output)
        self.assertIn("command substitution", output)
        self.assertIn("tar --null", output)
        self.assertIn("--files-from=-", output)
        self.assertIn(unsafe, output)


if __name__ == "__main__":
    unittest.main()
