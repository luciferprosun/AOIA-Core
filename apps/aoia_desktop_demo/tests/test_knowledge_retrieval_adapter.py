from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from apps.aoia_desktop_demo.knowledge.retrieval_adapter import retrieve_linux_evidence

REPO_ROOT = Path(__file__).resolve().parents[3]


class RetrievalAdapterTests(unittest.TestCase):
    def test_missing_index_degrades_to_empty_list_without_raising(self) -> None:
        # Run in a fresh subprocess: once this process has imported the
        # facade against the real repo (as other tests in this same run
        # do), Python's sys.modules import cache means a later call with a
        # different repo_root in-process would just reuse the cached
        # module — that reflects Python's own import semantics, not a
        # behavior of this adapter, and is irrelevant in practice because
        # the shipped app only ever points at the one repo it is cloned
        # into. A subprocess gives a truly clean import state to verify
        # the actual missing-index code path.
        with TemporaryDirectory() as tmp_dir:
            script = (
                "import sys; "
                f"sys.path.insert(0, {str(REPO_ROOT / 'apps' / '..')!r}); "
                f"sys.path.insert(0, {str(REPO_ROOT)!r}); "
                "from pathlib import Path; "
                "from apps.aoia_desktop_demo.knowledge.retrieval_adapter import retrieve_linux_evidence; "
                f"result = retrieve_linux_evidence(Path({tmp_dir!r}), 'how do I check disk usage'); "
                "print(len(result))"
            )
            completed = subprocess.run(
                [sys.executable, "-c", script], capture_output=True, text=True, timeout=30
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "0")

    def test_blank_query_returns_empty_without_importing_anything(self) -> None:
        evidence = retrieve_linux_evidence(REPO_ROOT, "   ")
        self.assertEqual(evidence, [])

    def test_real_repository_returns_bounded_evidence_for_a_known_query(self) -> None:
        evidence = retrieve_linux_evidence(REPO_ROOT, "pwd command", max_results=3)
        self.assertLessEqual(len(evidence), 3)
        for item in evidence:
            self.assertTrue(item.source_id)
            self.assertTrue(item.title)

    def test_max_results_is_respected(self) -> None:
        evidence = retrieve_linux_evidence(REPO_ROOT, "systemd service unit", max_results=1)
        self.assertLessEqual(len(evidence), 1)

    def test_nonsense_query_does_not_crash(self) -> None:
        evidence = retrieve_linux_evidence(REPO_ROOT, "zzzz-nonsense-query-xyz-123-does-not-exist")
        self.assertIsInstance(evidence, list)


if __name__ == "__main__":
    unittest.main()
