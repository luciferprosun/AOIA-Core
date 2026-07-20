from __future__ import annotations

import contextlib
import io
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from runtime.knowledge_modules.chat_cli import main
from runtime.knowledge_modules.german_law import GERMAN_LAW_EXPECTED_HEAD


ROOT = Path(__file__).resolve().parents[1]
GERMAN_REPOSITORY = "/home/l/AOIA_PRODUCTION/repos/AOIA-German-Law-Knowledge-Pack"
CORPUS_ROOT = "/home/l/AOIA_PRODUCTION/data/german-law-corpus"


def run_cli(*arguments: str) -> tuple[int, dict[str, object]]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = main(arguments)
    return code, json.loads(output.getvalue())


class KnowledgeChatCli1ATests(unittest.TestCase):
    def test_zero_module_dry_run_uses_provider_without_claiming_grounding(self):
        code, payload = run_cli(
            "--repository-root", str(ROOT),
            "--provider", "openrouter_chat",
            "--model", "explicit-test-model",
            "--question", "Explain evidence and authority.",
            "--format", "json",
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["selected_module_ids"], [])
        self.assertEqual(payload["knowledge_grounding_status"], "NO_KNOWLEDGE_MODULE_SELECTED")
        self.assertEqual(payload["provider_invocation_count"], 1)
        self.assertIsNone(payload["structured_answer"])

    def test_german_law_cli_builds_explicit_profile_configuration_and_dry_run_target(self):
        module = "de-law-federal-1a"
        payload_value = {
            "authority_status": "NON_AUTHORITATIVE_PROVIDER_OUTPUT",
            "context_package_hash": "a" * 64,
            "knowledge_grounding_status": "KNOWLEDGE_CONTEXT_PREPARED",
            "module_failures": [],
            "provider_invocation_count": 1,
            "provider_status": "DRY_RUN_ONLY",
            "selected_module_ids": [module],
            "structured_answer": None,
            "warnings": ["CURRENTNESS_NOT_VERIFIED"],
        }
        fake_result = SimpleNamespace(
            provider_status="DRY_RUN_ONLY",
            to_dict=lambda: payload_value,
        )
        with patch("runtime.knowledge_modules.chat_cli.KnowledgeProviderBridge1A") as bridge:
            bridge.return_value.execute.return_value = fake_result
            code, payload = run_cli(
                "--repository-root", str(ROOT),
                "--provider", "openrouter_chat",
                "--model", "explicit-test-model",
                "--enable-module", module,
                "--instance", f"{module}={module}-local",
                "--retrieval-mode", f"{module}=source-discovery",
                "--question", "What information does § 2 NachwG require an employer to document?",
                "--module-repository", f"{module}={GERMAN_REPOSITORY}",
                "--module-data-root", f"{module}={CORPUS_ROOT}",
                "--expected-module-head", f"{module}={GERMAN_LAW_EXPECTED_HEAD}",
                "--max-results", f"{module}=8",
                "--dry-run",
                "--format", "json",
            )
        self.assertEqual(code, 0)
        self.assertEqual(payload["selected_module_ids"], [module])
        self.assertEqual(payload["provider_status"], "DRY_RUN_ONLY")
        self.assertEqual(payload["provider_invocation_count"], 1)
        self.assertEqual(len(payload["context_package_hash"]), 64)
        self.assertIn("CURRENTNESS_NOT_VERIFIED", " ".join(payload["warnings"]))
        call = bridge.return_value.execute.call_args.kwargs
        self.assertEqual(call["profile"].enabled_selections[0].module_id, module)
        self.assertEqual(call["profile"].enabled_selections[0].per_module_max_results, 8)
        self.assertEqual(call["provider_target"].provider_id, "openrouter_chat")
        self.assertTrue(call["provider_target"].dry_run)
        self.assertIn(f"{module}-local", call["instance_configurations"])

    def test_unknown_provider_and_unselected_module_options_fail_closed(self):
        code, payload = run_cli(
            "--repository-root", str(ROOT),
            "--provider", "attacker_provider",
            "--model", "m",
            "--question", "q",
        )
        self.assertEqual(code, 2)
        self.assertEqual(payload["status"], "PROVIDER_TARGET_INVALID")

        code, payload = run_cli(
            "--repository-root", str(ROOT),
            "--provider", "openrouter_chat",
            "--model", "m",
            "--question", "q",
            "--max-results", "unselected-module=8",
        )
        self.assertEqual(code, 2)
        self.assertEqual(payload["status"], "PROFILE_INVALID")


if __name__ == "__main__":
    unittest.main()
