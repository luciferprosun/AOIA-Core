from __future__ import annotations

import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = PROJECT_ROOT / "web"
INDEX_PATH = WEB_DIR / "index.html"
APP_JS_PATH = WEB_DIR / "app.js"
STYLES_PATH = WEB_DIR / "styles.css"


class CptUiPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index_source = INDEX_PATH.read_text(encoding="utf-8")
        cls.app_source = APP_JS_PATH.read_text(encoding="utf-8")
        cls.styles_source = STYLES_PATH.read_text(encoding="utf-8")

    def test_ui_contains_critic_transform_control(self) -> None:
        self.assertIn("Critic Transform", self.index_source)
        self.assertIn('id="critic-transform"', self.index_source)
        self.assertIn('type="button"', self.index_source)

    def test_ui_contains_required_cpt_warning(self) -> None:
        self.assertIn("CPT improves critical framing, not truth", self.index_source)
        self.assertIn("Manual send required", self.index_source)

    def test_ui_calls_cpt_transform_endpoint(self) -> None:
        self.assertIn('"/api/cpt/transform"', self.app_source)
        self.assertIn('"balanced_critic"', self.app_source)

    def test_ui_does_not_auto_send_after_transform(self) -> None:
        function_body = self._function_body("transformComposerPrompt")

        self.assertNotIn("sendPrompt(", function_body)
        self.assertNotIn("requestSubmit(", function_body)
        self.assertNotIn('"/api/chat"', function_body)

    def test_ui_keeps_send_behavior_separate(self) -> None:
        transform_body = self._function_body("transformComposerPrompt")
        send_body = self._function_body("sendPrompt")

        self.assertIn('"/api/cpt/transform"', transform_body)
        self.assertIn('"/api/operator/chat"', send_body)
        self.assertIn('elements.chatForm.addEventListener("submit"', self.app_source)

    def test_ui_does_not_call_provider_model_endpoint_from_cpt_transform_function(self) -> None:
        function_body = self._function_body("transformComposerPrompt")
        forbidden = (
            '"/api/model"',
            '"/api/model-selection/propose"',
            '"/api/model-selection/approve-and-call"',
            "createSelectionProposal(",
            "approveAndCallProviderOnce(",
            "switchLegacyModel(",
        )

        offenders = [term for term in forbidden if term in function_body]
        self.assertEqual([], offenders)

    def test_ui_includes_human_review_and_canonical_status_text(self) -> None:
        self.assertIn("Human review required", self.app_source)
        self.assertIn("canonical_status", self.app_source)

    def test_no_new_external_urls_or_cdn_assets_in_web_files(self) -> None:
        combined = "\n".join((self.index_source, self.app_source, self.styles_source))
        urls = set(re.findall(r"https?://[^\"'\s)]+", combined))

        self.assertEqual(set(), urls)
        self.assertNotIn("cdn.", combined.lower())
        self.assertNotIn("unpkg.com", combined.lower())
        self.assertNotIn("jsdelivr", combined.lower())

    def test_ui_does_not_add_storage_or_telemetry(self) -> None:
        combined = "\n".join((self.index_source, self.app_source, self.styles_source))
        forbidden = ("localStorage", "sessionStorage", "document.cookie", "navigator.sendBeacon")

        offenders = [term for term in forbidden if term in combined]
        self.assertEqual([], offenders)

    def test_ui_avoids_hype_language(self) -> None:
        combined = "\n".join((self.index_source, self.app_source))
        forbidden = ("verified safe", "certified", "audit-grade", "truth secure")

        offenders = [term for term in forbidden if term in combined.lower()]
        self.assertEqual([], offenders)

    def _function_body(self, name: str) -> str:
        marker = f"async function {name}("
        start = self.app_source.index(marker)
        brace_start = self.app_source.index("{", start)
        depth = 0
        for index in range(brace_start, len(self.app_source)):
            char = self.app_source[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return self.app_source[brace_start : index + 1]
        raise AssertionError(f"function body not found: {name}")


if __name__ == "__main__":
    unittest.main()
