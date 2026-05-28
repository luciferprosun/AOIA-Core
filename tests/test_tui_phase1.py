from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    from tui.app import build_app
    from tui.widgets.log_panel import LogPanel
    from tui.widgets.status_panel import StatusPanel
except ModuleNotFoundError as exc:
    if exc.name == "textual":
        raise unittest.SkipTest("optional dependency textual is not installed") from exc
    raise


class TUIPhase1Tests(unittest.TestCase):
    def test_status_panel_renders_runtime_snapshot_fields(self) -> None:
        panel = StatusPanel()
        rendered = panel.render_status(
            {
                "model": "gemini/gemini-2.5-flash",
                "cwd": "/tmp/aoia",
                "session_log": "/tmp/session.jsonl",
                "knowledge_routing": {"enabled": True},
                "epistemic_safeguards": {
                    "kill_switch": False,
                    "disable_model": False,
                },
                "active_memory_hat": {"active_hat": "linux"},
            }
        )
        self.assertIn("gemini/gemini-2.5-flash", rendered)
        self.assertIn("retrieval: enabled", rendered)
        self.assertIn("approval_mode", rendered)
        self.assertIn("replay-only", rendered)

    def test_log_panel_filters_prompt_and_reasoning_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "session.jsonl"
            log_path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "timestamp": "2026-05-25T13:35:00",
                                "kind": "model_output",
                                "payload": {"raw_output": "hidden prompt internals"},
                            }
                        ),
                        json.dumps(
                            {
                                "timestamp": "2026-05-25T13:35:01",
                                "kind": "action_result",
                                "payload": {
                                    "action": {"action": "create_folder"},
                                    "result": {"success": True, "message": "Folder ready."},
                                },
                            }
                        ),
                    ]
                ),
                encoding="utf-8",
            )
            rendered = LogPanel().safe_tail(log_path)
        self.assertIn("action=create_folder", rendered)
        self.assertIn("Folder ready", rendered)
        self.assertNotIn("hidden prompt internals", rendered)
        self.assertNotIn("model_output", rendered)

    def test_app_builds_against_existing_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "runtime"
            project_dir.mkdir()
            app = build_app(project_dir=project_dir)
            status = app.runtime.snapshot_status()
        self.assertIn("session_log", status)
        self.assertIn("knowledge_routing", status)
        self.assertTrue(status["tools"])

    def test_provider_switching_uses_existing_provider_manager(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "runtime"
            project_dir.mkdir()
            app = build_app(project_dir=project_dir)
            selected = app.runtime.provider_manager.switch_model("gemini")
        self.assertEqual(selected, "gemini/gemini-2.5-flash")


if __name__ == "__main__":
    unittest.main()
