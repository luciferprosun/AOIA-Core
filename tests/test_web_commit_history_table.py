from __future__ import annotations

import unittest
from pathlib import Path

from runtime.webapp import _parse_commit_log_output, route_get_payload


REPO_ROOT = Path(__file__).resolve().parents[1]
WEBAPP_PATH = REPO_ROOT / "runtime" / "webapp.py"
APP_JS_PATH = REPO_ROOT / "web" / "app.js"
INDEX_PATH = REPO_ROOT / "web" / "index.html"
OPERATOR_CONFIG_PATH = REPO_ROOT / "web" / "operator_config.js"


class WebCommitHistoryTableTests(unittest.TestCase):
    def test_commit_log_parser_preserves_every_row(self) -> None:
        output = "\n".join(
            (
                "a" * 40 + "\taaaaaaa\t2026-07-05T18:54:06+02:00\tluciferprosun\tfirst subject",
                "b" * 40 + "\tbbbbbbb\t2026-07-05T18:06:20+02:00\tAOIA Test\tsecond subject",
            )
        )

        commits = _parse_commit_log_output(output)

        self.assertEqual(2, len(commits))
        self.assertEqual("aaaaaaa", commits[0]["short_sha"])
        self.assertEqual("second subject", commits[1]["subject"])

    def test_webapp_uses_read_only_git_adapter_for_commit_history(self) -> None:
        source = WEBAPP_PATH.read_text(encoding="utf-8")
        status, payload = route_get_payload("/api/commits")

        self.assertEqual(200, status)
        self.assertIn("commits", payload)
        self.assertIn('path == "/api/commits"', source)
        self.assertIn("GitReadCommand.COMMIT_LOG", source)
        self.assertIn("run_allowlisted_git_read", source)
        self.assertNotIn("git log --", source)

    def test_frontend_renders_commit_history_without_client_side_limit(self) -> None:
        index_source = INDEX_PATH.read_text(encoding="utf-8")
        app_source = APP_JS_PATH.read_text(encoding="utf-8")

        self.assertIn("commit-table-body", index_source)
        self.assertIn("/api/commits", app_source)
        self.assertIn("for (const commit of commits)", app_source)
        self.assertNotIn("commits.slice(", app_source)
        self.assertNotIn("MAX_COMMITS", app_source)

    def test_operator_ui_is_chat_first_with_hidden_diagnostics(self) -> None:
        index_source = INDEX_PATH.read_text(encoding="utf-8")

        self.assertIn("Operator Console", index_source)
        self.assertIn('class="chat-panel" id="chat"', index_source)
        self.assertIn('id="chat-history"', index_source)
        self.assertIn('id="chat-input"', index_source)
        self.assertIn('id="send-chat"', index_source)
        self.assertEqual(1, index_source.count('id="chat-history"'))
        self.assertEqual(3, index_source.count('class="observer-card"'))
        self.assertIn('id="settings-dialog"', index_source)
        self.assertIn('id="audit-dialog"', index_source)
        self.assertIn('id="observer-dialog"', index_source)
        self.assertNotIn('class="sidebar"', index_source)
        self.assertIn('id="router-proposal-result"', index_source)

    def test_operator_models_are_centralized_in_frontend_config(self) -> None:
        index_source = INDEX_PATH.read_text(encoding="utf-8")
        app_source = APP_JS_PATH.read_text(encoding="utf-8")
        config_source = OPERATOR_CONFIG_PATH.read_text(encoding="utf-8")

        self.assertIn('from "./operator_config.js"', app_source)
        self.assertIn("openai/gpt-4.1-mini", config_source)
        self.assertIn("openai/gpt-4.1-nano", config_source)
        self.assertIn("openai/gpt-5.4-mini", config_source)
        self.assertIn("openai/gpt-5.5", config_source)
        self.assertNotIn("openai/gpt-5.5", index_source)


if __name__ == "__main__":
    unittest.main()
