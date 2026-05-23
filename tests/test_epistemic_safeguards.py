import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main
from tools.executor import ExecutionEngine
from tools.memory import MemoryStore
from tools.validator import validate_action


class EpistemicSafeguardsTests(unittest.TestCase):
    def test_validate_action_normalizes_confidence_label(self) -> None:
        action = validate_action(
            {
                "action": "respond",
                "message": "I DO NOT KNOW",
                "reason": "No evidence.",
                "confidence": "LOW",
            }
        )
        self.assertEqual(action["confidence_label"], "low")

    def test_validate_action_defaults_unknown_confidence(self) -> None:
        action = validate_action(
            {
                "action": "respond",
                "message": "I DO NOT KNOW",
                "reason": "No evidence.",
                "confidence": "unsupported",
            }
        )
        self.assertEqual(action["confidence_label"], "unknown")

    def test_load_epistemic_safeguards_from_env(self) -> None:
        with patch.dict(
            os.environ,
            {
                "EPISTEMIC_KILL_SWITCH": "1",
                "EPISTEMIC_DISABLE_MODEL": "1",
                "EPISTEMIC_DISABLE_KNOWLEDGE_ROUTE": "1",
                "EPISTEMIC_DISABLE_MEMORY_HATS": "1",
                "EPISTEMIC_DISABLE_REASONING_TRACE": "1",
            },
            clear=False,
        ):
            safeguards = main.load_epistemic_safeguards()
        self.assertTrue(safeguards.kill_switch)
        self.assertTrue(safeguards.disable_model)
        self.assertTrue(safeguards.disable_knowledge)
        self.assertTrue(safeguards.disable_memory_hats)
        self.assertFalse(safeguards.reasoning_trace_enabled)
        self.assertTrue(safeguards.prefer_unknown)

    def test_memory_store_creates_evidence_and_reasoning_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            memory = MemoryStore(project_dir, project_dir)
            self.assertTrue(memory.vault_paths.evidence_dir.is_dir())
            self.assertTrue(memory.vault_paths.reasoning_dir.is_dir())

    def test_executor_respond_propagates_confidence_label(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            memory = MemoryStore(project_dir, project_dir)
            engine = ExecutionEngine(project_dir, memory)
            result = engine.execute(
                {
                    "action": "respond",
                    "message": "I DO NOT KNOW",
                    "reason": "No evidence.",
                    "confidence_label": "unknown",
                },
                require_approval=False,
            )
            self.assertEqual(result["confidence_label"], "unknown")


if __name__ == "__main__":
    unittest.main()
