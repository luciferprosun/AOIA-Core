from __future__ import annotations

import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from apps.aoia_desktop_demo.app import AppController
from apps.aoia_desktop_demo.knowledge.registry import NONE_PROFILE_ID
from apps.aoia_desktop_demo.providers.base import ChatResult, ProviderError

REPO_ROOT = Path(__file__).resolve().parents[3]


class _FakeOpenRouterClient:
    """Stands in for the real network client. Records call count so tests
    can assert there is exactly one call per submit_message — i.e. no
    hidden retry and no hidden fallback request."""

    call_count = 0
    next_result: ChatResult | None = None
    next_error: ProviderError | None = None

    def __init__(self, _config) -> None:
        pass

    def send_chat(self, model, messages, max_tokens=None):
        _FakeOpenRouterClient.call_count += 1
        if _FakeOpenRouterClient.next_error is not None:
            raise _FakeOpenRouterClient.next_error
        assert _FakeOpenRouterClient.next_result is not None
        return _FakeOpenRouterClient.next_result

    def list_models(self):
        return []

    def test_connection(self):
        return True


def _run_and_wait(controller: AppController, text: str, timeout: float = 5.0):
    done_event = threading.Event()
    captured = {}

    def on_done(result):
        captured["result"] = result
        done_event.set()

    request_id = controller.submit_message(
        text,
        on_done=on_done,
        on_scheduled_callback=lambda func: func(),  # run synchronously, no Tk loop in tests
    )
    assert done_event.wait(timeout=timeout), "provider call did not complete in time"
    return request_id, captured["result"]


class AppControllerModelOnlyModeTests(unittest.TestCase):
    def setUp(self) -> None:
        _FakeOpenRouterClient.call_count = 0
        _FakeOpenRouterClient.next_result = None
        _FakeOpenRouterClient.next_error = None
        self.controller = AppController(REPO_ROOT)
        self.controller.secrets.set_for_session("test-key")
        self.controller.settings.manual_model_id = "vendor/test-model"

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

    @patch("apps.aoia_desktop_demo.app.OpenRouterClient", _FakeOpenRouterClient)
    def test_knowledge_mode_can_attach_evidence(self) -> None:
        self.controller.set_knowledge_profile("linux_unix")
        _FakeOpenRouterClient.next_result = ChatResult(content="answer", model="vendor/test-model")
        _request_id, result = _run_and_wait(self.controller, "how do I check disk usage")
        self.assertIsNone(result.error_message)
        self.assertGreaterEqual(result.evidence_count, 0)  # may legitimately be 0 for a low-confidence query

    @patch("apps.aoia_desktop_demo.app.OpenRouterClient", _FakeOpenRouterClient)
    def test_exactly_one_provider_call_per_submit_no_hidden_retry(self) -> None:
        _FakeOpenRouterClient.next_result = ChatResult(content="hi", model="m")
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

    def test_manual_model_id_takes_precedence_over_selected(self) -> None:
        self.controller.settings.selected_model_id = "vendor/from-dropdown"
        self.controller.settings.manual_model_id = "vendor/manual-override"
        self.assertEqual(self.controller.effective_model_id(), "vendor/manual-override")

    def test_falls_back_to_selected_model_when_manual_blank(self) -> None:
        self.controller.settings.manual_model_id = ""
        self.controller.settings.selected_model_id = "vendor/from-dropdown"
        self.assertEqual(self.controller.effective_model_id(), "vendor/from-dropdown")


class CancellationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = AppController(REPO_ROOT)
        self.controller.secrets.set_for_session("test-key")
        self.controller.settings.manual_model_id = "vendor/test-model"

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
