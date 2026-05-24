from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.executor import ExecutionEngine
from tools.memory import MemoryStore


class MemoryLayerIsolationSmokeTests(unittest.TestCase):
    def test_execution_result_does_not_create_evidence_record(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            project_dir = Path(raw_tmp)
            memory_store = MemoryStore(project_dir=project_dir, cwd=project_dir)
            executor = ExecutionEngine(project_dir=project_dir, memory_store=memory_store)

            result = executor.execute(
                {"action": "respond", "message": "runtime response", "confidence_label": "high"},
                require_approval=False,
            )

            self.assertTrue(result["success"])
            self.assertTrue(memory_store.history_file.exists())
            self.assertFalse(memory_store.evidence_file.exists())


if __name__ == "__main__":
    unittest.main()

