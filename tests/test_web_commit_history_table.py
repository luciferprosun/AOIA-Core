from __future__ import annotations

import unittest
from pathlib import Path

from runtime.webapp import _parse_commit_log_output


REPO_ROOT = Path(__file__).resolve().parents[1]
WEBAPP_PATH = REPO_ROOT / "runtime" / "webapp.py"
APP_JS_PATH = REPO_ROOT / "web" / "app.js"
INDEX_PATH = REPO_ROOT / "web" / "index.html"


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

        self.assertIn('parsed.path == "/api/commits"', source)
        self.assertIn("GitReadCommand.COMMIT_LOG", source)
        self.assertIn("run_allowlisted_git_read", source)
        self.assertNotIn("git log --", source)

    def test_frontend_renders_commit_history_without_client_side_limit(self) -> None:
        index_source = INDEX_PATH.read_text(encoding="utf-8")
        app_source = APP_JS_PATH.read_text(encoding="utf-8")

        self.assertIn("commit-table-body", index_source)
        self.assertIn("/api/commits", app_source)
        self.assertIn("for (const commit of commits)", app_source)
        self.assertNotIn(".slice(0", app_source)
        self.assertNotIn("MAX_COMMITS", app_source)


if __name__ == "__main__":
    unittest.main()
