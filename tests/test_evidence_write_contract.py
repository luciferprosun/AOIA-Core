from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.memory import MemoryStore


class EvidenceWriteContractTests(unittest.TestCase):
    def _make_memory(self) -> MemoryStore:
        self._tmp = tempfile.TemporaryDirectory()
        project_dir = Path(self._tmp.name)
        return MemoryStore(project_dir=project_dir, cwd=project_dir)

    def tearDown(self) -> None:
        tmp = getattr(self, "_tmp", None)
        if tmp is not None:
            tmp.cleanup()

    def test_valid_evidence_write_succeeds(self) -> None:
        memory = self._make_memory()

        memory.append_evidence(
            "aoia_kernel_evidence",
            {
                "source": "aoia_kernel",
                "fingerprint": "some-non-empty-hash",
                "subject": "systemctl status",
            },
        )

        self.assertTrue(memory.evidence_file.exists())
        lines = memory.evidence_file.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)

    def test_missing_kind_is_rejected(self) -> None:
        memory = self._make_memory()

        with self.assertRaises(ValueError):
            memory.append_evidence(
                None,  # type: ignore[arg-type]
                {
                    "source": "aoia_kernel",
                    "fingerprint": "hash-1",
                },
            )

        self.assertFalse(memory.evidence_file.exists())

    def test_wrong_kind_is_rejected(self) -> None:
        memory = self._make_memory()

        with self.assertRaises(ValueError):
            memory.append_evidence(
                "runtime_action_result",
                {
                    "source": "aoia_kernel",
                    "fingerprint": "hash-2",
                },
            )

        self.assertFalse(memory.evidence_file.exists())

    def test_missing_source_is_rejected(self) -> None:
        memory = self._make_memory()

        with self.assertRaises(ValueError):
            memory.append_evidence(
                "aoia_kernel_evidence",
                {
                    "fingerprint": "hash-3",
                },
            )

        self.assertFalse(memory.evidence_file.exists())

    def test_unknown_sources_are_rejected(self) -> None:
        memory = self._make_memory()

        for source in ["gemini", "openrouter", "browser", "operator_note", "runtime_executor"]:
            with self.subTest(source=source):
                with self.assertRaises(ValueError):
                    memory.append_evidence(
                        "aoia_kernel_evidence",
                        {
                            "source": source,
                            "fingerprint": f"hash-{source}",
                        },
                    )
                self.assertFalse(memory.evidence_file.exists())

    def test_missing_fingerprint_is_rejected(self) -> None:
        memory = self._make_memory()

        with self.assertRaises(ValueError):
            memory.append_evidence(
                "aoia_kernel_evidence",
                {
                    "source": "aoia_kernel",
                },
            )

        self.assertFalse(memory.evidence_file.exists())

    def test_empty_fingerprint_is_rejected(self) -> None:
        memory = self._make_memory()

        with self.assertRaises(ValueError):
            memory.append_evidence(
                "aoia_kernel_evidence",
                {
                    "source": "aoia_kernel",
                    "fingerprint": "   ",
                },
            )

        self.assertFalse(memory.evidence_file.exists())

    def test_runtime_action_result_cannot_be_written_as_evidence(self) -> None:
        memory = self._make_memory()

        with self.assertRaises(ValueError):
            memory.append_evidence(
                "runtime_action_result",
                {
                    "source": "aoia_kernel",
                    "fingerprint": "hash-4",
                    "result": {"success": True},
                },
            )

        self.assertFalse(memory.evidence_file.exists())

    def test_provider_output_requires_explicit_external_evidence_classification(self) -> None:
        memory = self._make_memory()

        with self.assertRaises(ValueError):
            memory.append_evidence(
                "aoia_kernel_evidence",
                {
                    "source": "gemini",
                    "fingerprint": "provider-hash-1",
                    "provider": "gemini",
                },
            )

        memory.append_evidence(
            "aoia_kernel_evidence",
            {
                "source": "external_evidence_source",
                "fingerprint": "provider-hash-2",
                "provider": "gemini",
            },
        )

        self.assertTrue(memory.evidence_file.exists())
        lines = memory.evidence_file.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)

    def test_invalid_writes_do_not_append_partial_entries(self) -> None:
        memory = self._make_memory()

        with self.assertRaises(ValueError):
            memory.append_evidence(
                "aoia_kernel_evidence",
                {
                    "source": "browser",
                    "fingerprint": "hash-5",
                },
            )

        self.assertFalse(memory.evidence_file.exists())


if __name__ == "__main__":
    unittest.main()
