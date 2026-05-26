from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.memory import MemoryStore


class EvidenceBoundaryTests(unittest.TestCase):
    def test_append_evidence_rejects_non_evidence_kinds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            memory = MemoryStore(project_dir=project_dir, cwd=project_dir)

            with self.assertRaises(ValueError):
                memory.append_evidence(
                    "action_result",
                    {
                        "source": "aoia_kernel",
                        "fingerprint": "abc123",
                    },
                )

    def test_append_evidence_requires_source_and_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            memory = MemoryStore(project_dir=project_dir, cwd=project_dir)

            with self.assertRaises(ValueError):
                memory.append_evidence(
                    "aoia_kernel_evidence",
                    {
                        "source": "aoia_kernel",
                    },
                )

            with self.assertRaises(ValueError):
                memory.append_evidence(
                    "aoia_kernel_evidence",
                    {
                        "fingerprint": "abc123",
                    },
                )

    def test_append_evidence_accepts_allowed_kernel_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            memory = MemoryStore(project_dir=project_dir, cwd=project_dir)

            memory.append_evidence(
                "aoia_kernel_evidence",
                {
                    "source": "aoia_kernel",
                    "fingerprint": "abc123",
                    "query": "systemctl status",
                    "canonical_source": "runtime/knowledge/systemd/systemd-i-zarzdzanie-usugami.md",
                },
            )

            self.assertTrue(memory.evidence_file.exists())
            lines = memory.evidence_file.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)


if __name__ == "__main__":
    unittest.main()
