from __future__ import annotations

import threading
import unittest
import os
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from apps.aoia_desktop_demo.app import (
    PRE_DELIVERY_OBSERVER_COMPLETED,
    PRE_DELIVERY_OBSERVER_STARTED,
    PRE_DELIVERY_PRIMARY_DRAFT_COMPLETED,
    PRE_DELIVERY_PRIMARY_DRAFT_STARTED,
    PRE_DELIVERY_PRIMARY_FINAL_STARTED,
    AppController,
)
from apps.aoia_desktop_demo.critical_review import (
    ExecutionStatus,
    ObserverConfig,
    ReviewValidationError,
)
from apps.aoia_desktop_demo.knowledge.registry import NONE_PROFILE_ID
from apps.aoia_desktop_demo.providers.base import ChatResult, ProviderError
from apps.aoia_desktop_demo.providers.openrouter import OPENROUTER_BASE_URL

REPO_ROOT = Path(__file__).resolve().parents[3]


class _FakeOpenRouterClient:
    """Record the exact bounded provider sequence without network access."""

    call_count = 0
    calls: list[dict[str, object]] = []
    outcomes: list[ChatResult | ProviderError] = []
    next_result: ChatResult | None = None
    next_error: ProviderError | None = None
    instance_count = 0

    def __init__(self, _config) -> None:
        type(self).instance_count += 1
        self.instance_id = type(self).instance_count

    def _record_call(self, model, messages, max_tokens=None, *, structured=False, json_schema=None):
        _FakeOpenRouterClient.call_count += 1
        _FakeOpenRouterClient.calls.append(
            {
                "model": model,
                "messages": tuple(messages),
                "max_tokens": max_tokens,
                "client_instance_id": self.instance_id,
                "structured": structured,
                "json_schema": json_schema,
            }
        )
        if _FakeOpenRouterClient.outcomes:
            outcome = _FakeOpenRouterClient.outcomes[_FakeOpenRouterClient.call_count - 1]
            if isinstance(outcome, ProviderError):
                raise outcome
            return outcome
        if _FakeOpenRouterClient.next_error is not None:
            raise _FakeOpenRouterClient.next_error
        assert _FakeOpenRouterClient.next_result is not None
        return _FakeOpenRouterClient.next_result

    def send_chat(self, model, messages, max_tokens=None):
        return self._record_call(model, messages, max_tokens=max_tokens)

    def send_structured_chat(self, model, messages, *, json_schema, max_tokens=None):
        return self._record_call(
            model,
            messages,
            max_tokens=max_tokens,
            structured=True,
            json_schema=json_schema,
        )

    def list_models(self):
        return []

    def test_connection(self):
        return True


def _run_and_wait(controller: AppController, text: str, timeout: float = 5.0, **submit_kwargs):
    done_event = threading.Event()
    captured = {}

    def on_done(result):
        captured["result"] = result
        done_event.set()

    request_id = controller.submit_message(
        text,
        on_done=on_done,
        on_scheduled_callback=lambda func: func(),  # run synchronously, no Tk loop in tests
        **submit_kwargs,
    )
    assert done_event.wait(timeout=timeout), "provider call did not complete in time"
    return request_id, captured["result"]


def _structured_review(summary: str) -> str:
    return json.dumps(
        {
            "summary": summary,
            "findings": [
                {
                    "category": "logic",
                    "severity": "warning",
                    "title": f"{summary} finding",
                    "detail": "Revise this bounded point in the final answer.",
                }
            ],
            "uncertainty": [f"{summary} uncertainty"],
            "evidence_conflicts": [],
        }
    )


def _sequential_observer_configs() -> tuple[ObserverConfig, ...]:
    return (
        ObserverConfig(
            slot_id="observer-1",
            enabled=True,
            role_id="Logic & Claims",
            provider_connection_id="openrouter",
            model_id="vendor/logic-model",
        ),
        ObserverConfig(
            slot_id="observer-2",
            enabled=True,
            role_id="Safety & Authority",
            provider_connection_id="openrouter",
            model_id="vendor/safety-model",
        ),
        ObserverConfig(
            slot_id="observer-3",
            enabled=True,
            role_id="Evidence & Consistency",
            provider_connection_id="openrouter",
            model_id="vendor/evidence-model",
        ),
    )


class AppControllerModelOnlyModeTests(unittest.TestCase):
    def setUp(self) -> None:
        _FakeOpenRouterClient.call_count = 0
        _FakeOpenRouterClient.calls = []
        _FakeOpenRouterClient.outcomes = []
        _FakeOpenRouterClient.next_result = None
        _FakeOpenRouterClient.next_error = None
        _FakeOpenRouterClient.instance_count = 0
        self.controller = AppController(REPO_ROOT)
        self.controller.secrets.set_for_session("test-key")
        self.controller.settings.provider = "openrouter"
        self.controller.settings.api_base_url = OPENROUTER_BASE_URL
        self.controller.settings.manual_model_id = "vendor/test-model"
        self.controller.settings.pre_delivery_critical_loop_enabled = False

    def tearDown(self) -> None:
        self.controller.shutdown()

    @patch("apps.aoia_desktop_demo.app.OpenRouterClient", _FakeOpenRouterClient)
    def test_model_only_mode_sends_no_knowledge_evidence(self) -> None:
        self.controller.set_knowledge_profile(NONE_PROFILE_ID)
        _FakeOpenRouterClient.next_result = ChatResult(content="hello", model="vendor/test-model")
        _request_id, result = _run_and_wait(self.controller, "hello there")
        self.assertEqual(result.evidence_count, 0)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.chat_result.content, "hello")
        self.assertIsNotNone(result.completed_turn)
        self.assertEqual(result.completed_turn.original_prompt, "hello there")
        self.assertEqual(result.completed_turn.evidence_text, "")
        self.assertIsNone(result.completed_turn.knowledge_profile_id)

    @patch("apps.aoia_desktop_demo.app.OpenRouterClient", _FakeOpenRouterClient)
    def test_knowledge_mode_can_attach_evidence(self) -> None:
        self.controller.set_knowledge_profile("linux_unix")
        _FakeOpenRouterClient.next_result = ChatResult(content="answer", model="vendor/test-model")
        with patch(
            "apps.aoia_desktop_demo.app.retrieve_linux_evidence", return_value=[object()]
        ), patch(
            "apps.aoia_desktop_demo.app.build_knowledge_system_message",
            return_value="exact bounded primary evidence",
        ):
            _request_id, result = _run_and_wait(self.controller, "how do I check disk usage")
        self.assertIsNone(result.error_message)
        self.assertEqual(result.evidence_count, 1)
        self.assertEqual(result.completed_turn.evidence_text, "exact bounded primary evidence")
        self.assertEqual(result.completed_turn.knowledge_profile_id, "linux_unix")

    @patch("apps.aoia_desktop_demo.app.OpenRouterClient", _FakeOpenRouterClient)
    def test_exactly_one_provider_call_per_submit_no_hidden_retry(self) -> None:
        _FakeOpenRouterClient.next_result = ChatResult(content="hi", model="vendor/test-model")
        _run_and_wait(self.controller, "one message")
        self.assertEqual(_FakeOpenRouterClient.call_count, 1)

    @patch("apps.aoia_desktop_demo.app.OpenRouterClient", _FakeOpenRouterClient)
    def test_provider_error_is_surfaced_not_swallowed_or_retried(self) -> None:
        _FakeOpenRouterClient.next_error = ProviderError("simulated failure")
        _request_id, result = _run_and_wait(self.controller, "trigger failure")
        self.assertIsNotNone(result.error_message)
        self.assertEqual(_FakeOpenRouterClient.call_count, 1)

    def test_no_active_client_without_api_key(self) -> None:
        controller = AppController(REPO_ROOT)
        with self.assertRaises(ProviderError):
            controller.refresh_models()
        controller.shutdown()

    def test_route_is_inactive_until_manual_configuration_is_complete(self) -> None:
        controller = AppController(REPO_ROOT)
        self.assertFalse(controller.provider_route_is_eligible())
        controller.settings.provider = "openrouter"
        controller.settings.api_base_url = OPENROUTER_BASE_URL
        controller.settings.manual_model_id = "openai/gpt-4.1-nano"
        self.assertFalse(controller.provider_route_is_eligible())
        controller.secrets.set_for_session("sk-or-test-redacted")
        self.assertTrue(controller.provider_route_is_eligible())
        controller.shutdown()

    def test_environment_key_does_not_restore_a_connection(self) -> None:
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-test-redacted"}, clear=False):
            controller = AppController(REPO_ROOT)
            self.assertIsNone(controller.secrets.api_key)
            self.assertFalse(controller.provider_route_is_eligible())
            controller.shutdown()

    def test_manual_model_id_takes_precedence_over_selected(self) -> None:
        self.controller.settings.selected_model_id = "vendor/from-dropdown"
        self.controller.settings.manual_model_id = "vendor/manual-override"
        self.assertEqual(self.controller.effective_model_id(), "vendor/manual-override")

    def test_falls_back_to_selected_model_when_manual_blank(self) -> None:
        self.controller.settings.manual_model_id = ""
        self.controller.settings.selected_model_id = "vendor/from-dropdown"
        self.assertEqual(self.controller.effective_model_id(), "vendor/from-dropdown")


class PreDeliverySequentialControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        _FakeOpenRouterClient.call_count = 0
        _FakeOpenRouterClient.calls = []
        _FakeOpenRouterClient.outcomes = []
        _FakeOpenRouterClient.next_result = None
        _FakeOpenRouterClient.next_error = None
        _FakeOpenRouterClient.instance_count = 0
        self.controller = AppController(REPO_ROOT)
        self.controller.secrets.set_for_session("test-key")
        self.controller.settings.provider = "openrouter"
        self.controller.settings.api_base_url = OPENROUTER_BASE_URL
        self.controller.settings.manual_model_id = "vendor/primary-model"
        self.controller.settings.knowledge_profile_id = NONE_PROFILE_ID
        self.controller.settings.pre_delivery_critical_loop_enabled = True

    def tearDown(self) -> None:
        self.controller.shutdown()

    @patch("apps.aoia_desktop_demo.app.OpenRouterClient", _FakeOpenRouterClient)
    def test_one_send_runs_exactly_five_calls_and_returns_only_final_answer(self) -> None:
        _FakeOpenRouterClient.outcomes = [
            ChatResult(content="INTERNAL-DRAFT-NOT-FOR-CONVERSATION", model="vendor/primary-model"),
            ChatResult(content=_structured_review("observer one"), model="vendor/logic-model"),
            ChatResult(content=_structured_review("observer two"), model="vendor/safety-model"),
            ChatResult(content=_structured_review("observer three"), model="vendor/evidence-model"),
            ChatResult(content="FINAL-SUGGESTED-ANSWER", model="vendor/primary-model"),
        ]
        progress = []

        _request_id, result = _run_and_wait(
            self.controller,
            "original operator prompt",
            observer_configs=_sequential_observer_configs(),
            on_progress=progress.append,
        )

        self.assertEqual(_FakeOpenRouterClient.call_count, 5)
        self.assertEqual(
            [call["model"] for call in _FakeOpenRouterClient.calls],
            [
                "vendor/primary-model",
                "vendor/logic-model",
                "vendor/safety-model",
                "vendor/evidence-model",
                "vendor/primary-model",
            ],
        )
        self.assertEqual(
            [call["structured"] for call in _FakeOpenRouterClient.calls],
            [False, True, True, True, False],
        )
        self.assertEqual(
            _FakeOpenRouterClient.calls[0]["client_instance_id"],
            _FakeOpenRouterClient.calls[4]["client_instance_id"],
        )
        self.assertIsNone(result.error_message)
        self.assertTrue(result.pre_delivery_reviewed)
        self.assertEqual(result.chat_result.content, "FINAL-SUGGESTED-ANSWER")
        self.assertEqual(result.completed_turn.primary_response, "FINAL-SUGGESTED-ANSWER")
        self.assertEqual(len(result.observer_results), 3)
        self.assertEqual(
            [item.execution_status for item in result.observer_results],
            [ExecutionStatus.COMPLETED] * 3,
        )
        self.assertNotIn(
            "INTERNAL-DRAFT-NOT-FOR-CONVERSATION",
            "\n".join(entry.content for entry in self.controller.session.transcript),
        )
        self.controller.accept_completed_primary_turn(result)
        self.assertEqual(
            [entry.content for entry in self.controller.session.transcript],
            ["original operator prompt", "FINAL-SUGGESTED-ANSWER"],
        )

        final_payload = json.loads(_FakeOpenRouterClient.calls[4]["messages"][1].content)
        self.assertEqual(final_payload["original_prompt"], "original operator prompt")
        self.assertEqual(final_payload["initial_draft"], "INTERNAL-DRAFT-NOT-FOR-CONVERSATION")
        self.assertEqual(
            [report["summary"] for report in final_payload["observer_reports"]],
            ["observer one", "observer two", "observer three"],
        )
        self.assertEqual(
            [(item.stage, item.observer_index) for item in progress],
            [
                (PRE_DELIVERY_PRIMARY_DRAFT_STARTED, None),
                (PRE_DELIVERY_PRIMARY_DRAFT_COMPLETED, None),
                (PRE_DELIVERY_OBSERVER_STARTED, 1),
                (PRE_DELIVERY_OBSERVER_COMPLETED, 1),
                (PRE_DELIVERY_OBSERVER_STARTED, 2),
                (PRE_DELIVERY_OBSERVER_COMPLETED, 2),
                (PRE_DELIVERY_OBSERVER_STARTED, 3),
                (PRE_DELIVERY_OBSERVER_COMPLETED, 3),
                (PRE_DELIVERY_PRIMARY_FINAL_STARTED, None),
            ],
        )

    @patch("apps.aoia_desktop_demo.app.OpenRouterClient", _FakeOpenRouterClient)
    def test_observer_failure_stops_before_final_without_retry_or_fallback(self) -> None:
        _FakeOpenRouterClient.outcomes = [
            ChatResult(content="internal draft", model="vendor/primary-model"),
            ChatResult(content=_structured_review("observer one"), model="vendor/logic-model"),
            ProviderError("observer two failed"),
            ChatResult(content=_structured_review("observer three"), model="vendor/evidence-model"),
        ]

        _request_id, result = _run_and_wait(
            self.controller,
            "original operator prompt",
            observer_configs=_sequential_observer_configs(),
        )

        self.assertEqual(_FakeOpenRouterClient.call_count, 4)
        self.assertEqual(
            [call["model"] for call in _FakeOpenRouterClient.calls],
            [
                "vendor/primary-model",
                "vendor/logic-model",
                "vendor/safety-model",
                "vendor/evidence-model",
            ],
        )
        self.assertIsNone(result.chat_result)
        self.assertIsNone(result.completed_turn)
        self.assertFalse(result.pre_delivery_reviewed)
        self.assertIn("failed closed", result.error_message)
        self.assertEqual(
            [item.execution_status for item in result.observer_results],
            [ExecutionStatus.COMPLETED, ExecutionStatus.PROVIDER_ERROR, ExecutionStatus.COMPLETED],
        )

    @patch("apps.aoia_desktop_demo.app.OpenRouterClient", _FakeOpenRouterClient)
    def test_unstructured_observer_output_prevents_final_delivery(self) -> None:
        _FakeOpenRouterClient.outcomes = [
            ChatResult(content="internal draft", model="vendor/primary-model"),
            ChatResult(content="not structured json", model="vendor/logic-model"),
            ChatResult(content=_structured_review("observer two"), model="vendor/safety-model"),
            ChatResult(content=_structured_review("observer three"), model="vendor/evidence-model"),
        ]

        _request_id, result = _run_and_wait(
            self.controller,
            "original operator prompt",
            observer_configs=_sequential_observer_configs(),
        )

        self.assertEqual(_FakeOpenRouterClient.call_count, 4)
        self.assertIsNone(result.chat_result)
        self.assertIsNone(result.completed_turn)
        self.assertEqual(result.observer_results[0].execution_status, ExecutionStatus.UNSTRUCTURED_OUTPUT)
        self.assertEqual(
            [entry.content for entry in self.controller.session.transcript],
            ["original operator prompt"],
        )

    @patch("apps.aoia_desktop_demo.app.OpenRouterClient", _FakeOpenRouterClient)
    def test_provider_model_substitution_fails_closed_after_primary_call(self) -> None:
        _FakeOpenRouterClient.outcomes = [
            ChatResult(content="internal draft", model="vendor/unrequested-model"),
        ]

        _request_id, result = _run_and_wait(
            self.controller,
            "original operator prompt",
            observer_configs=_sequential_observer_configs(),
        )

        self.assertEqual(_FakeOpenRouterClient.call_count, 1)
        self.assertIsNone(result.chat_result)
        self.assertIsNone(result.completed_turn)
        self.assertIn("different model", result.error_message)

    @patch("apps.aoia_desktop_demo.app.OpenRouterClient", _FakeOpenRouterClient)
    def test_finalizer_failure_preserves_reviews_and_delivers_nothing(self) -> None:
        _FakeOpenRouterClient.outcomes = [
            ChatResult(content="internal draft", model="vendor/primary-model"),
            ChatResult(content=_structured_review("observer one"), model="vendor/logic-model"),
            ChatResult(content=_structured_review("observer two"), model="vendor/safety-model"),
            ChatResult(content=_structured_review("observer three"), model="vendor/evidence-model"),
            ProviderError("finalizer failed"),
        ]

        _request_id, result = _run_and_wait(
            self.controller,
            "original operator prompt",
            observer_configs=_sequential_observer_configs(),
        )

        self.assertEqual(_FakeOpenRouterClient.call_count, 5)
        self.assertIsNone(result.chat_result)
        self.assertIsNone(result.completed_turn)
        self.assertEqual(len(result.observer_results), 3)
        self.assertEqual(
            [entry.content for entry in self.controller.session.transcript],
            ["original operator prompt"],
        )

    @patch("apps.aoia_desktop_demo.app.OpenRouterClient", _FakeOpenRouterClient)
    def test_incomplete_observer_setup_is_rejected_before_state_or_calls(self) -> None:
        incomplete = _sequential_observer_configs()[:2]
        with self.assertRaises(ReviewValidationError):
            self.controller.submit_message(
                "must not be submitted",
                on_done=lambda _result: None,
                on_scheduled_callback=lambda func: func(),
                observer_configs=incomplete,
            )
        self.assertEqual(_FakeOpenRouterClient.call_count, 0)
        self.assertEqual(self.controller.session.transcript, [])


class CancellationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = AppController(REPO_ROOT)
        self.controller.secrets.set_for_session("test-key")
        self.controller.settings.provider = "openrouter"
        self.controller.settings.api_base_url = OPENROUTER_BASE_URL
        self.controller.settings.manual_model_id = "vendor/test-model"
        self.controller.settings.pre_delivery_critical_loop_enabled = False

    def tearDown(self) -> None:
        self.controller.shutdown()

    def test_canceled_request_result_is_ignored_by_session(self) -> None:
        request_id = self.controller.session.begin_request()
        self.controller.cancel_active_request()
        self.assertFalse(self.controller.session.is_current(request_id))

    def test_second_submit_blocked_while_one_is_active(self) -> None:
        self.controller.session.begin_request()
        result = self.controller.submit_message(
            "should be ignored while busy",
            on_done=lambda _r: None,
            on_scheduled_callback=lambda func: func(),
        )
        self.assertIsNone(result, "a second concurrent submit must be refused, not queued as a silent retry")


if __name__ == "__main__":
    unittest.main()
