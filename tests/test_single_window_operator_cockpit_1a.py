from __future__ import annotations

import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = PROJECT_ROOT / "web" / "index.html"
APP_PATH = PROJECT_ROOT / "web" / "app.js"
STYLES_PATH = PROJECT_ROOT / "web" / "styles.css"


class SingleWindowOperatorCockpit1ATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = INDEX_PATH.read_text(encoding="utf-8")
        cls.app = APP_PATH.read_text(encoding="utf-8")
        cls.styles = STYLES_PATH.read_text(encoding="utf-8")
        cls.combined = "\n".join((cls.index, cls.app, cls.styles))

    def test_one_conversation_and_exactly_three_observer_cards(self) -> None:
        self.assertEqual(1, self.index.count('id="chat-history"'))
        self.assertEqual(1, self.index.count('id="chat-form"'))
        self.assertEqual(3, self.index.count('class="observer-card"'))
        self.assertIn("one conversation", self.index.lower())
        self.assertNotIn('class="sidebar"', self.index)

    def test_viewport_is_contained_and_scroll_is_intentional(self) -> None:
        self.assertRegex(self.styles, r"html,\s*\nbody\s*\{[^}]*overflow:\s*hidden")
        self.assertRegex(self.styles, r"\.app-shell\s*\{[^}]*height:\s*100dvh")
        self.assertRegex(self.styles, r"\.workspace\s*\{[^}]*overflow:\s*hidden")
        self.assertRegex(self.styles, r"\.chat-history\s*\{[^}]*overflow-y:\s*auto")
        self.assertRegex(self.styles, r"\.message-row\s*\{[^}]*flex:\s*0 0 auto")
        self.assertRegex(self.styles, r"\.drawer-dialog\s*\{[^}]*height:\s*100dvh")
        self.assertRegex(self.styles, r"\.drawer-body\s*\{[^}]*overflow-y:\s*auto")

    def test_mobile_observers_use_horizontal_scroll_snap_rail(self) -> None:
        mobile = self.styles[self.styles.index("@media (max-width: 820px)") :]
        self.assertIn(".observer-rail", mobile)
        self.assertIn("overflow-x: auto", mobile)
        self.assertIn("scroll-snap-type: x mandatory", mobile)
        self.assertIn("width: 100vw", mobile)

    def test_settings_audit_and_observer_details_are_modal_dialogs(self) -> None:
        for dialog_id in ("settings-dialog", "audit-dialog", "observer-dialog"):
            self.assertIn(f'<dialog class="drawer-dialog" id="{dialog_id}"', self.index)
        self.assertIn("dialog.showModal()", self.app)
        self.assertIn('dialog.addEventListener("close"', self.app)
        self.assertIn("window.requestAnimationFrame(() => opener.focus())", self.app)
        self.assertIn("opener.focus()", self.app)
        self.assertEqual(4, self.index.count('role="tab"'))

    def test_primary_and_observers_have_independent_configuration(self) -> None:
        self.assertIn('id="router-provider-select"', self.index)
        self.assertIn('id="router-model-select"', self.index)
        for index in range(1, 4):
            self.assertIn(f'id="observer-provider-{index}"', self.index)
            self.assertIn(f'id="observer-model-{index}"', self.index)
            self.assertIn(f'id="observer-role-{index}"', self.index)
        self.assertIn("hydrateObserverSelectors", self.app)
        self.assertIn("renderObservers", self.app)

    def test_observers_and_provider_output_are_explicitly_non_authoritative(self) -> None:
        self.assertEqual(4, self.index.count("NO AUTHORITY"))
        self.assertIn("PROVIDER OUTPUT · UNTRUSTED", self.index)
        self.assertIn("Observer configuration and reports cannot vote themselves into approval", self.index)
        self.assertIn("no critic result is fabricated", self.app)

    def test_add_api_flow_is_masked_inert_and_clears_transient_fields(self) -> None:
        self.assertIn('id="api-key" type="password"', self.index)
        self.assertIn("function detectProviderCandidate({ key, baseUrl })", self.app)
        self.assertIn("Explicitly confirm provider", self.index)
        self.assertIn("no secure secret backend", self.index)
        clear_body = self._function_body("clearApiTransient")
        self.assertIn('elements.apiKey.value = ""', clear_body)
        self.assertIn('elements.baseUrl.value = ""', clear_body)
        self.assertIn('elements.providerConfirm.value = ""', clear_body)
        self.assertIn("finally", self._event_handler_body("elements.apiForm", '"submit"'))
        self.assertIn("clearApiTransient()", self._event_handler_body("elements.cancelApi", '"click"'))

    def test_frontend_has_no_secret_persistence_logging_or_direct_provider_request(self) -> None:
        forbidden = (
            "localStorage",
            "sessionStorage",
            "indexedDB",
            "document.cookie",
            "console.log",
            "console.debug",
            "fetch(\"https://",
            "fetch('https://",
        )
        self.assertEqual([], [term for term in forbidden if term in self.combined])
        api_submit = self._event_handler_body("elements.apiForm", '"submit"')
        self.assertNotIn("fetchJson(", api_submit)
        self.assertNotIn("fetch(", api_submit)

    def test_send_and_cpt_use_only_existing_explicit_contracts(self) -> None:
        send_body = self._async_function_body("sendPrompt")
        transform_body = self._async_function_body("transformComposerPrompt")
        self.assertIn('"/api/operator/chat"', send_body)
        self.assertIn("isControlledChatModel(selected)", send_body)
        self.assertIn('"/api/cpt/transform"', transform_body)
        self.assertNotIn("sendPrompt(", transform_body)
        self.assertNotIn("requestSubmit(", transform_body)
        self.assertIn('event.key === "Enter" && !event.shiftKey', self.app)

    def test_read_only_endpoint_contracts_are_reused(self) -> None:
        for path in (
            "/api/operator/status",
            "/api/router/status",
            "/api/model-catalog",
            "/api/evidence/sample",
            "/api/boundaries",
            "/api/agent-loop/status",
            "/api/audit/status",
            "/api/commits",
            "/api/router/preview",
        ):
            self.assertIn(path, self.app)

    def test_no_automatic_retry_fallback_streaming_or_provider_switch(self) -> None:
        self.assertIn("NO AUTO-FALLBACK", self.index)
        self.assertIn("No automatic fallback, retry, streaming", self.index)
        self.assertNotRegex(self.app, r"setInterval\s*\(")
        self.assertNotIn("WebSocket", self.app)
        self.assertNotIn("EventSource", self.app)
        self.assertNotIn("retryCount", self.app)

    def test_no_external_runtime_assets_or_new_framework(self) -> None:
        urls = set(re.findall(r"https?://[^\"'\s)]+", self.combined))
        self.assertEqual(set(), urls)
        for framework in ("react", "vue", "angular", "svelte", "tailwind"):
            self.assertNotIn(framework, self.combined.lower())

    def _function_body(self, name: str) -> str:
        return self._body_from_marker(f"function {name}(")

    def _async_function_body(self, name: str) -> str:
        return self._body_from_marker(f"async function {name}(")

    def _event_handler_body(self, element: str, event: str) -> str:
        return self._body_from_marker(f"{element}.addEventListener({event},")

    def _body_from_marker(self, marker: str) -> str:
        start = self.app.index(marker)
        brace_start = self.app.index("{", start)
        depth = 0
        for index in range(brace_start, len(self.app)):
            char = self.app[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return self.app[brace_start : index + 1]
        raise AssertionError(f"body not found: {marker}")


if __name__ == "__main__":
    unittest.main()
