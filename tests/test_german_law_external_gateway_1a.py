from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from runtime.knowledge_modules.contracts import KnowledgeModuleConfiguration, KnowledgeModuleError
from runtime.knowledge_modules.external_gateway import GermanLawExternalGateway
from runtime.knowledge_modules.selection import KnowledgeModuleQuery
from tests.knowledge_module_test_support_1a import HEAD_A, SHA_A, SHA_B


def configuration(repository: Path, **changes) -> KnowledgeModuleConfiguration:
    values = {
        "schema_version": "knowledge-module-configuration-1a",
        "module_repository_path": str(repository),
        "corpus_data_root": "/tmp/synthetic-corpus",
        "approved_resolved_corpus_path": "/tmp/synthetic-corpus",
        "expected_repository_head": HEAD_A,
        "expected_module_id": "de-law-federal-1a",
        "expected_module_version": "1a",
        "expected_descriptor_hash": SHA_A,
        "expected_corpus_snapshot_id": "snapshot-1a",
        "expected_corpus_snapshot_ids": ("snapshot-1a",),
        "expected_temporal_snapshot_id": "temporal-1a",
        "expected_eu_snapshot_id": "eu-1a",
        "expected_eu_snapshot_manifest_hash": SHA_B,
        "expected_manifest_hashes": (("manifest.json", SHA_A),),
        "query_timeout_seconds": 3,
        "verification_timeout_seconds": 4,
        "maximum_stdout_bytes": 4096,
        "maximum_stderr_bytes": 1024,
    }
    values.update(changes)
    return KnowledgeModuleConfiguration(**values)


class GermanLawExternalGateway1ATests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="aoia-german-gateway-")
        self.root = Path(self.temporary.name)
        (self.root / "src/german_law_corpus").mkdir(parents=True)
        (self.root / "src/german_law_corpus/cli.py").write_text("# fixture\n", encoding="utf-8")
        self.config = configuration(self.root)
        self.gateway = GermanLawExternalGateway()

    def tearDown(self):
        self.temporary.cleanup()

    def test_only_three_fixed_operations_and_fixed_module_are_constructed(self):
        query = KnowledgeModuleQuery(question="§ 1 GG", retrieval_mode="SOURCE_DISCOVERY")
        for operation, expected_subcommand in (
            ("descriptor", "hat-info"),
            ("verify", "hat-verify"),
            ("query", "hat-query"),
        ):
            command = self.gateway._command(
                self.config,
                self.root,
                operation,
                query if operation == "query" else None,
            )
            self.assertEqual(command[1:4], ("-m", "german_law_corpus.cli", expected_subcommand))
            self.assertNotIn("sh", command)
            self.assertNotIn("bash", command)
        with self.assertRaises(KnowledgeModuleError):
            self.gateway._invoke(self.config, "arbitrary-command", None)

    def test_subprocess_uses_shell_false_fixed_cwd_and_minimal_environment(self):
        captured = {}

        def fake_run(command, **kwargs):
            captured.update(command=command, **kwargs)
            return SimpleNamespace(stdout=b"{}", stderr=b"", returncode=0)

        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "must-not-cross-boundary",
                "GITHUB_TOKEN": "must-not-cross-boundary",
            },
            clear=False,
        ):
            with patch("runtime.knowledge_modules.external_gateway.subprocess.run", fake_run):
                self.gateway.descriptor(self.config)
        self.assertIs(captured["shell"], False)
        self.assertEqual(captured["cwd"], str(self.root.resolve()))
        self.assertEqual(captured["stdin"], subprocess.DEVNULL)
        self.assertTrue(captured["close_fds"])
        self.assertNotIn("OPENAI_API_KEY", captured["env"])
        self.assertNotIn("GITHUB_TOKEN", captured["env"])
        self.assertEqual(
            set(captured["env"]),
            {
                "LANG",
                "LC_ALL",
                "PYTHONDONTWRITEBYTECODE",
                "PYTHONHASHSEED",
                "PYTHONNOUSERSITE",
                "PYTHONPATH",
                "PYTHONUTF8",
                "TZ",
            },
        )

    def test_timeout_output_limits_and_malformed_json_fail_closed(self):
        cases = (
            (subprocess.TimeoutExpired(("python",), 3), "MODULE_TIMEOUT"),
            (SimpleNamespace(stdout=b"x" * 4097, stderr=b"", returncode=0), "MODULE_OUTPUT_LIMIT_EXCEEDED"),
            (SimpleNamespace(stdout=b"{}", stderr=b"x" * 1025, returncode=0), "MODULE_OUTPUT_LIMIT_EXCEEDED"),
            (SimpleNamespace(stdout=b"{malformed", stderr=b"", returncode=0), "MODULE_OUTPUT_MALFORMED"),
            (SimpleNamespace(stdout=b'{"a":1,"a":2}', stderr=b"", returncode=0), "MODULE_OUTPUT_MALFORMED"),
        )
        for outcome, status in cases:
            with self.subTest(status=status, outcome=type(outcome).__name__):
                if isinstance(outcome, BaseException):
                    mocked = patch(
                        "runtime.knowledge_modules.external_gateway.subprocess.run",
                        side_effect=outcome,
                    )
                else:
                    mocked = patch(
                        "runtime.knowledge_modules.external_gateway.subprocess.run",
                        return_value=outcome,
                    )
                with mocked as run:
                    with self.assertRaises(KnowledgeModuleError) as caught:
                        self.gateway.descriptor(self.config)
                self.assertEqual(caught.exception.status, status)
                self.assertEqual(run.call_count, 1)

    def test_query_flags_are_allowlisted_and_derived_only_from_validated_query(self):
        query = KnowledgeModuleQuery(
            question="§ 2 NachwG",
            retrieval_mode="VERIFIED_AS_OF",
            as_of_date="2022-09-01",
            jurisdictions=("DE-BUND",),
            document_types=("STATUTE_OR_REGULATION",),
            source_classes=("OFFICIAL_CONSOLIDATED_TEXT",),
            languages=("de",),
            max_results=8,
            max_excerpt_characters=1000,
            max_total_context_characters=8000,
        )
        command = self.gateway._command(self.config, self.root, "query", query)
        self.assertIn("--mode=verified-as-of", command)
        self.assertIn("--as-of=2022-09-01", command)
        self.assertIn("--max-results=8", command)
        self.assertEqual(command[-2], "--data-root=/tmp/synthetic-corpus")
        self.assertEqual(command[-1], "--format=json")

    def test_repository_symlink_is_rejected_before_process_start(self):
        link = self.root.parent / f"{self.root.name}-link"
        link.symlink_to(self.root, target_is_directory=True)
        try:
            linked = configuration(link)
            with patch("runtime.knowledge_modules.external_gateway.subprocess.run") as run:
                with self.assertRaises(KnowledgeModuleError) as caught:
                    self.gateway.descriptor(linked)
            self.assertEqual(caught.exception.status, "MODULE_NOT_AVAILABLE")
            run.assert_not_called()
        finally:
            link.unlink()


if __name__ == "__main__":
    unittest.main()
