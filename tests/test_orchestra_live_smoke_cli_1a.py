from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from runtime.orchestra_live_smoke_cli import (
    PROJECT_ROOT,
    RUN_ACTION_PHRASE,
    run_cli,
)
from runtime.providers.orchestra_live_service import OrchestraLiveWebError


PREVIEW_HASH = "a" * 64


def _preview_response() -> dict[str, object]:
    return {
        "preview": {
            "preview_hash": PREVIEW_HASH,
            "orchestra_run_id": "orchestra-cli-1",
            "run_hash": "b" * 64,
            "role_selection_hash": "c" * 64,
            "expires_at_epoch": 2_000_000_000,
            "authority_status": "NON_AUTHORITATIVE",
            "planned_calls": [
                {
                    "call_index": 0,
                    "stage_id": "stage-main",
                    "operator_role": "MAIN",
                    "connection_id": "connection-a",
                    "model_profile_id": "model-main",
                    "remote_model_id": "vendor/main",
                    "timeout_seconds": 9,
                    "maximum_output_tokens": 64,
                },
                {
                    "call_index": 1,
                    "stage_id": "stage-critic",
                    "operator_role": "CRITIC",
                    "connection_id": "connection-a",
                    "model_profile_id": "model-critic",
                    "remote_model_id": "vendor/critic",
                    "timeout_seconds": 9,
                    "maximum_output_tokens": 64,
                },
            ],
        },
        "provider_call_permitted": False,
        "human_action_required": True,
    }


def _run_response() -> dict[str, object]:
    return {
        "session": {
            "orchestra_run_id": "orchestra-cli-1",
            "stage_results": [
                {
                    "operator_role": "MAIN",
                    "response_text": "untrusted draft",
                    "trust_status": "UNTRUSTED",
                    "authoritative": False,
                }
            ],
            "authority_status": "NON_AUTHORITATIVE",
            "human_review_required": True,
        },
        "final_draft": "untrusted draft",
        "trust_status": "UNTRUSTED",
        "authority_status": "NON_AUTHORITATIVE",
        "authoritative": False,
        "human_review_required": True,
        "automatic_fallback_used": False,
        "automatic_retry_used": False,
    }


class _FakeService:
    def __init__(self) -> None:
        self.preview_requests: list[dict[str, object]] = []
        self.run_requests: list[dict[str, object]] = []

    def create_preview(self, payload: dict[str, object]) -> dict[str, object]:
        self.preview_requests.append(payload)
        return _preview_response()

    def run_preview(self, payload: dict[str, object]) -> dict[str, object]:
        self.run_requests.append(payload)
        return _run_response()


class ControlledLiveSmokeCliTests(unittest.TestCase):
    def _run(
        self,
        service: _FakeService,
        answers: list[str],
        *,
        argv: list[str] | None = None,
    ) -> tuple[int, list[str], list[str]]:
        outputs: list[str] = []
        errors: list[str] = []
        remaining = iter(answers)
        result = run_cli(
            argv
            or [
                "--prompt",
                "Prepare a bounded demonstration.",
                "--model",
                "model-main=MAIN",
                "--model",
                "model-critic=CRITIC",
                "--timeout-seconds",
                "9",
                "--maximum-output-tokens",
                "64",
            ],
            service=service,
            input_fn=lambda _prompt: next(remaining),
            output_fn=outputs.append,
            error_fn=errors.append,
        )
        return result, outputs, errors

    def test_live_call_requires_exact_preview_hash_confirmation(self) -> None:
        service = _FakeService()
        result, _outputs, errors = self._run(
            service,
            ["0" * 64, RUN_ACTION_PHRASE],
        )
        self.assertEqual(2, result)
        self.assertEqual([], service.run_requests)
        self.assertIn("did not match", errors[0])

    def test_live_call_also_requires_explicit_run_orchestra_phrase(self) -> None:
        service = _FakeService()
        result, _outputs, errors = self._run(service, [PREVIEW_HASH, "run"])
        self.assertEqual(2, result)
        self.assertEqual([], service.run_requests)
        self.assertIn("was not entered", errors[0])

    def test_exact_confirmations_start_one_service_run_with_no_routing_options(self) -> None:
        service = _FakeService()
        result, outputs, errors = self._run(
            service,
            [PREVIEW_HASH, RUN_ACTION_PHRASE],
        )
        self.assertEqual(0, result)
        self.assertEqual([], errors)
        self.assertEqual(
            {
                "source_prompt": "Prepare a bounded demonstration.",
                "selections": [
                    {"model_profile_id": "model-main", "role": "MAIN"},
                    {"model_profile_id": "model-critic", "role": "CRITIC"},
                ],
                "timeout_seconds": 9,
                "maximum_output_tokens": 64,
            },
            service.preview_requests[0],
        )
        self.assertEqual(
            [
                {
                    "preview_hash": PREVIEW_HASH,
                    "confirmation_hash": PREVIEW_HASH,
                    "confirmed_preview_hash": PREVIEW_HASH,
                    "explicit_run_action": True,
                }
            ],
            service.run_requests,
        )
        plan = json.loads(outputs[0])
        result_payload = json.loads(outputs[1])
        self.assertFalse(plan["provider_call_permitted"])
        self.assertTrue(plan["human_action_required"])
        self.assertFalse(result_payload["authoritative"])
        self.assertTrue(result_payload["human_review_required"])
        self.assertFalse(result_payload["automatic_fallback_used"])
        self.assertFalse(result_payload["automatic_retry_used"])

    def test_prompt_file_is_bounded_and_forwarded_without_restart(self) -> None:
        service = _FakeService()
        with tempfile.TemporaryDirectory() as temporary:
            prompt_path = Path(temporary) / "prompt.txt"
            prompt_path.write_text("Prompt loaded for this one run.", encoding="utf-8")
            result, _outputs, errors = self._run(
                service,
                [PREVIEW_HASH, RUN_ACTION_PHRASE],
                argv=[
                    "--prompt-file",
                    str(prompt_path),
                    "--model",
                    "model-main=MAIN",
                    "--model",
                    "model-auditor=AUDITOR",
                ],
            )
        self.assertEqual(0, result)
        self.assertEqual([], errors)
        self.assertEqual(
            "Prompt loaded for this one run.",
            service.preview_requests[0]["source_prompt"],
        )

    def test_duplicate_model_and_unsupported_role_fail_before_preview(self) -> None:
        for second in ("model-main=CRITIC", "model-critic=EXECUTOR"):
            with self.subTest(second=second):
                service = _FakeService()
                result, _outputs, _errors = self._run(
                    service,
                    [],
                    argv=[
                        "--prompt",
                        "Prompt",
                        "--model",
                        "model-main=MAIN",
                        "--model",
                        second,
                    ],
                )
                self.assertEqual(2, result)
                self.assertEqual([], service.preview_requests)
                self.assertEqual([], service.run_requests)

    def test_unsupported_role_value_is_not_echoed_to_stderr(self) -> None:
        secret_like_role = "sk-cli-role-secret-material-000004"
        service = _FakeService()
        result, outputs, errors = self._run(
            service,
            [],
            argv=[
                "--prompt",
                "Prompt",
                "--model",
                "model-main=MAIN",
                "--model",
                f"model-critic={secret_like_role}",
            ],
        )
        self.assertEqual(2, result)
        self.assertNotIn(secret_like_role, "\n".join(outputs + errors))
        self.assertEqual([], service.preview_requests)

    def test_service_error_details_are_not_rendered(self) -> None:
        secret = "sk-cli-secret-must-not-appear"

        class _FailingService(_FakeService):
            def create_preview(self, payload: dict[str, object]) -> dict[str, object]:
                raise OrchestraLiveWebError(f"credential failure: {secret}")

        result, outputs, errors = self._run(_FailingService(), [])
        rendered = "\n".join(outputs + errors)
        self.assertEqual(1, result)
        self.assertNotIn(secret, rendered)
        self.assertIn("failed closed", rendered)

    def test_structured_stage_failure_is_safe_and_returns_nonzero(self) -> None:
        class _StageFailureService(_FakeService):
            def run_preview(self, payload: dict[str, object]) -> dict[str, object]:
                self.run_requests.append(payload)
                return {
                    "ok": False,
                    "failed_stage": {
                        "reason_code": "ORCHESTRA_EXACT_STAGE_FAILED",
                        "stage_id": "stage-critic",
                        "call_index": 1,
                        "operator_role": "CRITIC",
                        "connection_id": "connection-a",
                        "model_profile_id": "model-critic",
                        "session_consumed": True,
                        "trust_status": "UNTRUSTED",
                        "authority_status": "NON_AUTHORITATIVE",
                        "authoritative": False,
                        "automatic_fallback_used": False,
                        "automatic_retry_used": False,
                        "human_review_required": True,
                    },
                    "authoritative": False,
                    "authority_status": "NON_AUTHORITATIVE",
                    "human_review_required": True,
                    "automatic_fallback_used": False,
                    "automatic_retry_used": False,
                }

        result, outputs, errors = self._run(
            _StageFailureService(),
            [PREVIEW_HASH, RUN_ACTION_PHRASE],
        )
        self.assertEqual(1, result)
        self.assertEqual([], errors)
        payload = json.loads(outputs[-1])
        self.assertEqual("ORCHESTRA_LIVE_STAGE_FAILED", payload["event"])
        self.assertEqual("model-critic", payload["failed_stage"]["model_profile_id"])
        self.assertFalse(payload["automatic_retry_used"])

    def test_cli_resolves_the_same_canonical_repository_root(self) -> None:
        self.assertEqual(
            Path(__file__).resolve().parents[1],
            PROJECT_ROOT,
        )


if __name__ == "__main__":
    unittest.main()
