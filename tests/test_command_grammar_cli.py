import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class CommandGrammarCliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "runtime.tools.command_grammar_cli", *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_systemctl_status_returns_json_family_or_exact(self):
        result = self.run_cli("systemctl status sshd")
        self.assertEqual(0, result.returncode, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("systemctl status sshd", payload[0]["input"])
        self.assertEqual("systemctl", payload[0]["base"])
        self.assertIn(payload[0]["status"], {"exact", "family"})

    def test_dnf_status_is_not_exact(self):
        result = self.run_cli("dnf status httpd")
        self.assertEqual(0, result.returncode, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("dnf", payload[0]["base"])
        self.assertIn(payload[0]["status"], {"suspicious", "reject"})
        self.assertNotEqual("exact", payload[0]["status"])

    def test_no_args_exits_two_and_prints_usage(self):
        result = self.run_cli()
        self.assertEqual(2, result.returncode)
        self.assertIn("Usage:", result.stderr)

    def test_output_parses_as_json(self):
        result = self.run_cli("podman ps")
        self.assertEqual(0, result.returncode, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIsInstance(payload, list)
        self.assertEqual("podman ps", payload[0]["input"])

    def test_cli_does_not_execute_shell_commands(self):
        marker = Path("/tmp/aoia_should_not_exist")
        if marker.exists():
            marker.unlink()

        result = self.run_cli("echo safe && touch /tmp/aoia_should_not_exist")
        self.assertEqual(0, result.returncode, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("suspicious", payload[0]["status"])
        self.assertFalse(marker.exists())

    def test_direct_file_execution_works(self):
        result = subprocess.run(
            [
                sys.executable,
                "runtime/tools/command_grammar_cli.py",
                "firewall-cmd --list-all",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("firewall-cmd", payload[0]["base"])


if __name__ == "__main__":
    unittest.main()
