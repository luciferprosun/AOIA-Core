import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.executor import ExecutionEngine
from tools.memory import MemoryStore


class ExecutorContainmentTests(unittest.TestCase):
    def test_action_results_are_replay_only_not_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            desktop_dir = project_dir / "Desktop"
            desktop_dir.mkdir()

            memory = MemoryStore(project_dir, project_dir)
            engine = ExecutionEngine(project_dir, memory)
            with (
                patch.dict(os.environ, {"AOIA_LEGACY_FILESYSTEM_ENABLED": "1"}),
                patch.object(engine, "_request_approval", return_value=True),
            ):
                result = engine.execute(
                    {
                        "action": "create_folder",
                        "path": str(desktop_dir / "AI_TEST"),
                        "reason": "Create desktop folder.",
                    },
                    require_approval=False,
                )

            self.assertTrue(result["success"])
            self.assertTrue((desktop_dir / "AI_TEST").is_dir())
            self.assertTrue(memory.memory.recent_outputs)
            self.assertEqual(len(list(memory.paths.command_logs_dir.glob("*.json"))), 1)
            self.assertFalse(memory.evidence_file.exists())

            history_lines = memory.history_file.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(history_lines), 1)
            history_record = json.loads(history_lines[0])
            authority = history_record["payload"]["authority"]
            self.assertEqual(history_record["kind"], "action_result")
            self.assertEqual(authority["classification"], "operational_event")
            self.assertEqual(authority["retention"], "replay_only")
            self.assertTrue(authority["non_authoritative"])
            self.assertFalse(authority["canonical_evidence"])


if __name__ == "__main__":
    unittest.main()
