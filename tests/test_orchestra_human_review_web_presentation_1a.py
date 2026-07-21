from __future__ import annotations

import json
import unittest
from http import HTTPStatus
from pathlib import Path
from unittest.mock import patch

from runtime.epistemic_orchestra.human_review_workspace import (
    DESCRIPTIVE_AGREEMENT_LABEL,
    HUMAN_COMPARISON_WARNING,
)
from runtime.webapp import CodexStyleHandler, route_get_payload, route_post_payload
from tests.test_orchestra_session_view_1a import _SessionHarness


ROOT = Path(__file__).resolve().parents[1]


class OrchestraHumanReviewWebPresentation1ATests(_SessionHarness):
    def test_read_only_endpoint_returns_sanitized_canonical_workspace(self) -> None:
        preview, _snapshot, _view = self._complete()
        session_id = self._session_id(preview)
        calls_after_run = tuple(self.fake_invoker.calls)

        with patch("runtime.webapp.get_orchestra_service", return_value=self.service):
            first_status, first = route_get_payload(
                f"/api/orchestra/sessions/{session_id}/human-review"
            )
            second_status, second = route_get_payload(
                f"/api/orchestra/sessions/{session_id}/human-review"
            )

        self.assertEqual(HTTPStatus.OK, first_status)
        self.assertEqual(HTTPStatus.OK, second_status)
        self.assertEqual(first, second)
        self.assertEqual(session_id, first["session_id"])
        self.assertEqual(HUMAN_COMPARISON_WARNING, first["human_comparison_warning"])
        self.assertEqual(calls_after_run, tuple(self.fake_invoker.calls))
        self.assertNotIn(self.API_KEY, json.dumps(first, sort_keys=True))

    def test_endpoint_rejects_malformed_and_unknown_session_identifiers(self) -> None:
        malformed_paths = (
            "/api/orchestra/sessions//human-review",
            "/api/orchestra/sessions/a/b/human-review",
            "/api/orchestra/sessions/%2e%2e/human-review",
            "/api/orchestra/sessions/contains%20space/human-review",
        )
        with patch("runtime.webapp.get_orchestra_service", return_value=self.service):
            for path in malformed_paths:
                with self.subTest(path=path):
                    status, payload = route_get_payload(path)
                    self.assertEqual(HTTPStatus.BAD_REQUEST, status)
                    self.assertEqual("session identifier is malformed", payload["error"])

            status, payload = route_get_payload(
                "/api/orchestra/sessions/orchestra-web-unknown/human-review"
            )
        self.assertEqual(HTTPStatus.NOT_FOUND, status)
        self.assertEqual("Orchestra session was not found", payload["error"])
        self.assertNotIn("orchestra-web-unknown", json.dumps(payload))

    def test_no_human_review_write_endpoint_is_registered(self) -> None:
        path = "/api/orchestra/sessions/orchestra-web-example/human-review"
        status, payload = route_post_payload(path, {})

        self.assertEqual(HTTPStatus.NOT_FOUND, status)
        self.assertEqual({"ok": False, "error": "Not found"}, payload)

    def test_dynamic_handler_keeps_human_review_endpoint_loopback_local(self) -> None:
        preview = self._create_preview()
        path = (
            f"/api/orchestra/sessions/{self._session_id(preview)}/human-review"
        )
        with patch("runtime.webapp.get_orchestra_service", return_value=self.service):
            allowed_writes: list[tuple[HTTPStatus, dict[str, object]]] = []
            allowed = object.__new__(CodexStyleHandler)
            allowed.path = path
            allowed.headers = {"Host": "127.0.0.1:4311"}
            allowed.client_address = ("127.0.0.1", 12345)
            allowed._write_json = lambda status, payload: allowed_writes.append(
                (status, payload)
            )
            CodexStyleHandler.do_GET(allowed)
            self.assertEqual(HTTPStatus.OK, allowed_writes[0][0])

            denied_writes: list[tuple[HTTPStatus, dict[str, object]]] = []
            denied = object.__new__(CodexStyleHandler)
            denied.path = path
            denied.headers = {"Host": "attacker.example:4311"}
            denied.client_address = ("127.0.0.1", 12345)
            denied._write_json = lambda status, payload: denied_writes.append(
                (status, payload)
            )
            CodexStyleHandler.do_GET(denied)
            self.assertEqual(HTTPStatus.FORBIDDEN, denied_writes[0][0])
        self.assertEqual([], self.fake_invoker.calls)

    def test_frontend_contains_exact_non_authority_labels_and_warning(self) -> None:
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")

        self.assertIn(HUMAN_COMPARISON_WARNING, html)
        self.assertIn(DESCRIPTIVE_AGREEMENT_LABEL, html)
        self.assertIn("CRITIC RESULT — NON-AUTHORITATIVE METADATA", html)
        self.assertIn("AUDIT RESULT — EVIDENCE ONLY", html)
        self.assertIn('id="open-orchestra-human-review"', html)
        self.assertIn('id="orchestra-compare-candidate-a"', html)
        self.assertIn('id="orchestra-compare-candidate-b"', html)

    def test_provider_html_and_script_payloads_use_inert_text_rendering(self) -> None:
        payload_text = '<img src=x onerror="providerCall()"><script>gate=true</script>'
        preview, _snapshot, _view = self._complete(
            roles=("MAIN", "CRITIC"),
            responses_by_role={"MAIN": payload_text},
        )
        workspace = self.service.get_orchestra_human_review_workspace(
            self._session_id(preview)
        )
        script = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        start = script.index("function appendComparisonTextCandidate")
        end = script.index("async function loadOrchestraSessionView", start)
        workspace_renderer = script[start:end]

        self.assertIn("<script>", workspace["candidates"][0]["response_text"])
        self.assertIn("response.textContent =", workspace_renderer)
        self.assertNotIn("innerHTML", workspace_renderer)
        self.assertNotIn("insertAdjacentHTML", workspace_renderer)
        self.assertNotIn("DOMParser", workspace_renderer)

    def test_workspace_selection_is_ephemeral_and_never_sent_to_server(self) -> None:
        script = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        start = script.index("function clearOrchestraHumanReviewWorkspace")
        end = script.index("async function loadOrchestraSessionView", start)
        workspace_script = script[start:end]

        self.assertIn("replaceChildren()", workspace_script)
        self.assertIn("renderSelectedOrchestraComparison", workspace_script)
        self.assertIn("/human-review", workspace_script)
        self.assertNotIn('method: "POST"', workspace_script)
        self.assertNotIn("localStorage", script)
        self.assertNotIn("sessionStorage", script)
        self.assertNotIn("setInterval(", script)
        self.assertNotIn("/api/orchestra/run", workspace_script)
        self.assertNotIn("/api/orchestra/preview", workspace_script)
        self.assertIn(
            "elements.orchestraSessionId.value.trim() !== sessionId",
            workspace_script,
        )

    def test_session_identity_changes_clear_stale_workspace_state(self) -> None:
        script = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        clear_function = script.split(
            "function clearOrchestraSessionView()", 1
        )[1].split("function renderOrchestraSessionView", 1)[0]
        input_handler = script.split(
            'elements.orchestraSessionId.addEventListener("input", () => {', 1
        )[1].split("});", 1)[0]

        self.assertIn("clearOrchestraHumanReviewWorkspace();", clear_function)
        self.assertIn("clearOrchestraSessionView();", input_handler)
        self.assertIn(
            "Session ID changed while the read-only view was loading.",
            script,
        )


if __name__ == "__main__":
    unittest.main()
