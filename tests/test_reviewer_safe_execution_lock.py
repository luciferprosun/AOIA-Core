import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.executor import ExecutionEngine
from tools.memory import MemoryStore
from tools.shell_tools import shell_execute


class ReviewerSafeExecutionLockTests(unittest.TestCase):
    def test_shell_execute_blocks_before_subprocess_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(subprocess, "run") as subprocess_run:
                result = shell_execute("pwd", Path(tmp))

        self.assertFalse(result["success"])
        self.assertTrue(result["blocked"])
        self.assertEqual(result["mode"], "reviewer_safe_blocked")
        self.assertIsNone(result["exit_code"])
        self.assertEqual(result["stdout"], "")
        self.assertEqual(result["stderr"], "")
        subprocess_run.assert_not_called()

    def test_execution_engine_shell_action_does_not_reach_subprocess_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            memory = MemoryStore(project_dir, project_dir)
            engine = ExecutionEngine(project_dir, memory)

            with patch.object(subprocess, "run") as subprocess_run:
                result = engine.execute(
                    {
                        "action": "shell_execute",
                        "command": "pwd",
                        "reason": "Reviewer-safe lock regression.",
                        "requires_confirmation": False,
                    }
                )

        self.assertFalse(result["success"])
        self.assertTrue(result["blocked"])
        self.assertEqual(result["mode"], "reviewer_safe_blocked")
        subprocess_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
