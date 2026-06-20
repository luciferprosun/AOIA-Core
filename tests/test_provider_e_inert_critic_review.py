from __future__ import annotations

import ast
import socket
import subprocess
import tempfile
import unittest
import urllib.request
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from runtime.provider_controlled_flow import (
    NO_ARTIFACT_WRITE,
    NO_EXECUTION,
    REVIEW_REQUIRED,
    run_mock_provider_controlled_flow,
)
from runtime.provider_critic_review import (
    AUTHORITY_CLAIM_DETECTED,
    HUMAN_REVIEW_REQUIRED,
    INERT_PROVIDER_CRITIC_REVIEW,
    LIVE_CALL_NOT_USED,
    NO_ARTIFACT_WRITE_PERMITTED,
    NO_EXECUTION_PERMITTED,
    PROVIDER_OUTPUT_UNTRUSTED,
    REGISTRY_DECISION_REQUIRED,
    UNSAFE_INSTRUCTION_DETECTED,
    ProviderCriticReviewBlocked,
    review_provider_controlled_flow,
)
from runtime.provider_request_flow import (
    UNTRUSTED_PROVIDER_OUTPUT,
    ProviderRequest,
    decide_mock_provider_request,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "provider_critic_review.py"
UNSAFE_TEXT = (
    "APPROVED; human approved; execute this; write file; ignore safety; "
    "bypass; run command; secret; API key"
)


class ProviderEInertCriticReviewTests(unittest.TestCase):
    def test_accepts_valid_provider_d_flow_and_preserves_inert_status(self):
        flow = self.make_flow()
        review = review_provider_controlled_flow(flow)

        self.assertEqual(INERT_PROVIDER_CRITIC_REVIEW, review.critic_label)
        self.assertEqual(REVIEW_REQUIRED, review.status)
        self.assertEqual(NO_EXECUTION, review.execution_status)
        self.assertEqual(NO_ARTIFACT_WRITE, review.artifact_write_status)
        self.assertEqual(UNTRUSTED_PROVIDER_OUTPUT, review.output_trust_label)
        self.assertTrue(review.requires_human_review)
        self.assertTrue(review.blocking)
        self.assertFalse(review.approved)
        self.assertFalse(review.rejected)
        self.assertFalse(review.authoritative)
        self.assertFalse(review.gate_eligible)
        self.assertFalse(review.write_eligible)
        self.assertFalse(review.execution_occurred)
        self.assertFalse(review.artifact_write_occurred)
        self.assertFalse(review.provider_live_call_used)

    def test_preserves_request_provider_and_registry_metadata(self):
        flow = self.make_flow()
        review = review_provider_controlled_flow(flow)

        self.assertEqual(flow.request_id, review.request_id)
        self.assertEqual(flow.request_hash, review.request_hash)
        self.assertEqual(flow.provider_id, review.provider_id)
        self.assertEqual(flow.request_metadata, review.request_metadata)
        self.assertEqual(
            flow.registry_decision_summary,
            review.registry_decision_summary,
        )
        self.assertEqual(flow.provider_output.output_id, review.provider_output_id)
        self.assertEqual(
            flow.provider_output.output_hash,
            review.provider_output_hash,
        )
        self.assertEqual(flow.provider_output.model_label, review.model_label)
        self.assertEqual(
            flow.provider_output.provider_metadata,
            review.provider_metadata,
        )
        self.assertEqual(
            flow.local_visible_review.projection_hash,
            review.local_visible_metadata["projection_hash"],
        )

    def test_baseline_findings_record_inert_boundary(self):
        review = review_provider_controlled_flow(self.make_flow())

        expected = {
            PROVIDER_OUTPUT_UNTRUSTED,
            HUMAN_REVIEW_REQUIRED,
            NO_EXECUTION_PERMITTED,
            NO_ARTIFACT_WRITE_PERMITTED,
            REGISTRY_DECISION_REQUIRED,
            LIVE_CALL_NOT_USED,
        }
        self.assertTrue(expected.issubset(set(review.risk_categories)))

    def test_detects_authority_execution_write_and_unsafe_phrases_only_as_findings(self):
        review = review_provider_controlled_flow(
            self.make_flow(mock_response_text=UNSAFE_TEXT)
        )
        by_category = {finding.category: finding for finding in review.findings}

        self.assertEqual(
            ("approved", "human approved"),
            by_category[AUTHORITY_CLAIM_DETECTED].matched_phrases,
        )
        self.assertEqual(
            (
                "execute this",
                "write file",
                "ignore safety",
                "bypass",
                "run command",
                "secret",
                "api key",
            ),
            by_category[UNSAFE_INSTRUCTION_DETECTED].matched_phrases,
        )
        self.assertEqual(REVIEW_REQUIRED, review.status)
        self.assertEqual(UNTRUSTED_PROVIDER_OUTPUT, review.output_trust_label)
        self.assertFalse(review.approved)
        self.assertFalse(review.authoritative)
        self.assertFalse(review.gate_eligible)
        self.assertFalse(review.write_eligible)
        self.assertFalse(review.execution_occurred)
        self.assertFalse(review.artifact_write_occurred)

    def test_findings_do_not_call_network_shell_gate_or_write_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            before = sorted(Path(tmpdir).rglob("*"))
            with patch.object(
                urllib.request,
                "urlopen",
                side_effect=AssertionError("network called"),
            ) as urlopen_mock, patch.object(
                socket,
                "create_connection",
                side_effect=AssertionError("network called"),
            ) as socket_mock, patch.object(
                subprocess,
                "run",
                side_effect=AssertionError("command executed"),
            ) as run_mock, patch(
                "runtime.safety.approval_artifact_gate.evaluate_pre_artifact_approval_gate",
                side_effect=AssertionError("gate called"),
            ) as gate_mock:
                review = review_provider_controlled_flow(
                    self.make_flow(
                        mock_response_text=UNSAFE_TEXT,
                        proposed_artifact_path=str(Path(tmpdir) / "forbidden"),
                        proposed_artifact_content=UNSAFE_TEXT,
                    )
                )
            after = sorted(Path(tmpdir).rglob("*"))

        self.assertEqual(before, after)
        self.assertFalse(review.approved)
        self.assertFalse(review.gate_eligible)
        self.assertFalse(review.write_eligible)
        urlopen_mock.assert_not_called()
        socket_mock.assert_not_called()
        run_mock.assert_not_called()
        gate_mock.assert_not_called()

    def test_missing_or_blocked_controlled_flow_fails_closed(self):
        with self.assertRaises(ProviderCriticReviewBlocked):
            review_provider_controlled_flow(None)

        request = self.make_request(live_call_requested=True)
        blocked = run_mock_provider_controlled_flow(
            request=request,
            registry_decision=decide_mock_provider_request(request),
            model_label="mock-provider-e-model",
            mock_response_text="Blocked input.",
        )
        with self.assertRaises(ProviderCriticReviewBlocked):
            review_provider_controlled_flow(blocked)

    def test_live_call_approval_gate_and_write_claims_fail_closed(self):
        flow = self.make_flow()
        invalid_variants = (
            replace(flow, provider_live_call_used=True),
            replace(flow, approved=True),
            replace(flow, gate_eligible=True),
            replace(flow, write_eligible=True),
            replace(flow, execution_occurred=True),
            replace(flow, artifact_write_occurred=True),
            replace(flow, trust_label="TRUSTED"),
            replace(
                flow,
                candidate=replace(flow.candidate, provider_output_trusted=True),
            ),
            replace(
                flow,
                proposal_conversion=replace(
                    flow.proposal_conversion,
                    execution_permitted=True,
                ),
            ),
            replace(
                flow,
                review_packet=replace(
                    flow.review_packet,
                    pre_artifact_gate_passed=True,
                ),
            ),
            replace(
                flow,
                local_visible_review=replace(
                    flow.local_visible_review,
                    approved=True,
                ),
            ),
        )
        for invalid in invalid_variants:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ProviderCriticReviewBlocked):
                    review_provider_controlled_flow(invalid)

    def test_review_is_deterministic_and_does_not_mutate_provider_d_result(self):
        flow = self.make_flow(mock_response_text=UNSAFE_TEXT)
        before = flow.to_dict()

        first = review_provider_controlled_flow(flow)
        second = review_provider_controlled_flow(flow)

        self.assertEqual(first, second)
        self.assertEqual(first.critic_review_hash, second.critic_review_hash)
        self.assertEqual(first.critic_review_id, second.critic_review_id)
        self.assertEqual(before, flow.to_dict())

    def test_runtime_has_no_network_shell_browser_secret_or_authority_capability(self):
        source = RUNTIME_FILE.read_text(encoding="utf-8")
        lowered = source.lower()
        forbidden_terms = (
            "subprocess",
            "os.system",
            "popen",
            "socket",
            "urllib",
            "httpx",
            "playwright",
            "selenium",
            "eval(",
            "exec(",
            "webbrowser",
            "getenv",
            "environ",
            "openai",
            "gemini",
            "anthropic",
            "openrouter",
            "approval_artifact_gate",
            "gated_durable_artifact_flow",
            "human_decision",
            "write_text(",
            "write_bytes(",
            "mkdir(",
        )
        for term in forbidden_terms:
            self.assertNotIn(term, lowered)

        tree = ast.parse(source)
        allowed_import_roots = {
            "__future__",
            "dataclasses",
            "enum",
            "hashlib",
            "json",
            "re",
            "runtime",
            "typing",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".", 1)[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                roots = {(node.module or "").split(".", 1)[0]}
            else:
                continue
            self.assertTrue(roots.issubset(allowed_import_roots))

    def make_request(self, **overrides):
        values = {
            "provider_id": "openrouter",
            "task_text": "Prepare an inert critic review proposal.",
            "purpose": "Provider-E inert critic review",
            "caller_label": "provider-e-test",
            "live_call_requested": False,
            "metadata": {
                "trace": "provider-e",
                "request_kind": "inert-critic-review",
            },
        }
        values.update(overrides)
        return ProviderRequest(**values)

    def make_flow(self, **overrides):
        request = overrides.pop("request", self.make_request())
        values = {
            "request": request,
            "registry_decision": decide_mock_provider_request(request),
            "model_label": "mock-provider-e-model",
            "mock_response_text": "Deterministic provider proposal for critic review.",
        }
        values.update(overrides)
        return run_mock_provider_controlled_flow(**values)


if __name__ == "__main__":
    unittest.main()
