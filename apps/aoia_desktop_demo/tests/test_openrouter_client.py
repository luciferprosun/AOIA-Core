"""OpenRouter client tests using a mocked transport.

No real network call is made: ``urllib.request.urlopen`` is patched in
every test. These tests must never contact the real OpenRouter API.
"""

from __future__ import annotations

import json
import unittest
import urllib.error
from unittest.mock import patch

from apps.aoia_desktop_demo.providers.base import ChatMessage, ModelInfo, ProviderError
from apps.aoia_desktop_demo.providers.openrouter import OpenRouterClient, OpenRouterConfig


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def read(self, _n: int | None = None) -> bytes:
        return self._body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_exc) -> bool:
        return False


def _client(api_key: str = "test-key-123") -> OpenRouterClient:
    return OpenRouterClient(OpenRouterConfig(api_key=api_key, timeout_seconds=5.0))


class RequestConstructionTests(unittest.TestCase):
    @patch("apps.aoia_desktop_demo.providers.openrouter.urllib.request.urlopen")
    def test_send_chat_builds_expected_request(self, mock_urlopen) -> None:
        mock_urlopen.return_value = FakeResponse(
            {"model": "test/model", "choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}], "usage": {}}
        )
        client = _client(api_key="sk-secret-value")
        client.send_chat("test/model", [ChatMessage(role="user", content="hello")])

        self.assertEqual(mock_urlopen.call_count, 1)
        sent_request = mock_urlopen.call_args[0][0]
        self.assertEqual(sent_request.full_url, "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(sent_request.get_header("Authorization"), "Bearer sk-secret-value")
        self.assertEqual(sent_request.get_header("Content-type"), "application/json")
        self.assertEqual(
            sent_request.get_header("X-openrouter-title"),
            "AOIA Control Chat Competition Demo",
        )
        body = json.loads(sent_request.data.decode("utf-8"))
        self.assertEqual(body["model"], "test/model")
        self.assertEqual(body["stream"], False)
        self.assertEqual(body["messages"], [{"role": "user", "content": "hello"}])

    @patch("apps.aoia_desktop_demo.providers.openrouter.urllib.request.urlopen")
    def test_no_retry_on_failure(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = urllib.error.URLError("boom")
        client = _client()
        with self.assertRaises(ProviderError):
            client.send_chat("m", [ChatMessage(role="user", content="hi")])
        self.assertEqual(mock_urlopen.call_count, 1, "client must not retry automatically")


class ResponseParsingTests(unittest.TestCase):
    @patch("apps.aoia_desktop_demo.providers.openrouter.urllib.request.urlopen")
    def test_parses_valid_response(self, mock_urlopen) -> None:
        mock_urlopen.return_value = FakeResponse(
            {
                "model": "test/model",
                "choices": [{"message": {"content": "  hello there  "}, "finish_reason": "stop"}],
                "usage": {"total_tokens": 12},
            }
        )
        result = _client().send_chat("test/model", [ChatMessage(role="user", content="hi")])
        self.assertEqual(result.content, "hello there")
        self.assertEqual(result.usage["total_tokens"], 12)

    @patch("apps.aoia_desktop_demo.providers.openrouter.urllib.request.urlopen")
    def test_missing_choices_raises_provider_error(self, mock_urlopen) -> None:
        mock_urlopen.return_value = FakeResponse({"model": "m"})
        with self.assertRaises(ProviderError):
            _client().send_chat("m", [ChatMessage(role="user", content="hi")])

    @patch("apps.aoia_desktop_demo.providers.openrouter.urllib.request.urlopen")
    def test_non_dict_top_level_payload_raises(self, mock_urlopen) -> None:
        class ListResponse(FakeResponse):
            def __init__(self) -> None:
                self._body = b"[1, 2, 3]"

        mock_urlopen.return_value = ListResponse()
        with self.assertRaises(ProviderError):
            _client().send_chat("m", [ChatMessage(role="user", content="hi")])

    def test_empty_messages_rejected_without_network_call(self) -> None:
        with self.assertRaises(ProviderError):
            _client().send_chat("m", [])

    def test_empty_model_rejected_without_network_call(self) -> None:
        with self.assertRaises(ProviderError):
            _client().send_chat("", [ChatMessage(role="user", content="hi")])


class ErrorRedactionTests(unittest.TestCase):
    @patch("apps.aoia_desktop_demo.providers.openrouter.urllib.request.urlopen")
    def test_http_error_body_is_redacted(self, mock_urlopen) -> None:
        error_body = b'{"error": "Authorization: Bearer sk-leaked1234567890 invalid"}'

        def _raise(*_args, **_kwargs):
            raise urllib.error.HTTPError(
                url="https://openrouter.ai/api/v1/chat/completions",
                code=401,
                msg="Unauthorized",
                hdrs=None,
                fp=__import__("io").BytesIO(error_body),
            )

        mock_urlopen.side_effect = _raise
        with self.assertRaises(ProviderError) as ctx:
            _client().send_chat("m", [ChatMessage(role="user", content="hi")])
        self.assertNotIn("sk-leaked1234567890", str(ctx.exception))


class ModelCatalogTests(unittest.TestCase):
    @patch("apps.aoia_desktop_demo.providers.openrouter.urllib.request.urlopen")
    def test_list_models_parses_pricing_and_filters_free(self, mock_urlopen) -> None:
        mock_urlopen.return_value = FakeResponse(
            {
                "data": [
                    {"id": "vendor/free-model", "name": "Free Model", "context_length": 8192, "pricing": {"prompt": "0", "completion": "0"}},
                    {"id": "vendor/paid-model", "name": "Paid Model", "context_length": 4096, "pricing": {"prompt": "0.002", "completion": "0.006"}},
                    {"id": "", "name": "Bad Entry"},
                ]
            }
        )
        models = _client().list_models()
        self.assertEqual(len(models), 2, "the entry with an empty id must be skipped")
        free = [model for model in models if model.is_free]
        self.assertEqual([model.id for model in free], ["vendor/free-model"])

    @patch("apps.aoia_desktop_demo.providers.openrouter.urllib.request.urlopen")
    def test_list_models_rejects_malformed_payload(self, mock_urlopen) -> None:
        mock_urlopen.return_value = FakeResponse({"unexpected": True})
        with self.assertRaises(ProviderError):
            _client().list_models()


class ModelInfoTests(unittest.TestCase):
    def test_is_free_false_for_unparseable_price(self) -> None:
        model = ModelInfo(id="x", name="x", prompt_price="not-a-number", completion_price="0")
        self.assertFalse(model.is_free)


if __name__ == "__main__":
    unittest.main()
