from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = REPO_ROOT / "web" / "index.html"
APP_PATH = REPO_ROOT / "web" / "app.js"


class OrchestraUserProviderWebUi1ATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index_source = INDEX_PATH.read_text(encoding="utf-8")
        cls.app_source = APP_PATH.read_text(encoding="utf-8")

    def test_connection_form_has_required_fields_and_masks_api_key(self) -> None:
        for field_id in (
            "provider-connection-id",
            "provider-connection-name",
            "provider-api-style",
            "provider-base-url",
            "provider-api-key",
        ):
            with self.subTest(field_id=field_id):
                self.assertIn(f'id="{field_id}"', self.index_source)

        key_input = re.search(
            r'<input\s+id="provider-api-key"(?P<attributes>.*?)\s*/>',
            self.index_source,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(key_input)
        self.assertIn('type="password"', key_input.group("attributes"))
        self.assertIn('autocomplete="new-password"', key_input.group("attributes"))
        self.assertIn('elements.providerApiKey.value = "";', self.app_source)

    def test_model_profile_form_has_connection_model_and_allowed_role_fields(self) -> None:
        for field_id in (
            "model-profile-id",
            "model-profile-connection",
            "model-profile-name",
            "model-remote-id",
            "model-allowed-roles",
        ):
            with self.subTest(field_id=field_id):
                self.assertIn(f'id="{field_id}"', self.index_source)

        for role in ("MAIN", "CRITIC", "AUDITOR", "SYNTHESIZER"):
            with self.subTest(role=role):
                self.assertIn(f'<option value="{role}">{role}</option>', self.index_source)
        self.assertIn('name="allowed_roles" multiple', self.index_source)

    def test_orchestra_table_has_exact_operator_columns(self) -> None:
        columns = (
            "Selected",
            "Model display name",
            "Connection name",
            "Remote model ID",
            "Connection status",
            "Model status",
            "Assigned role",
            "Last connection test",
        )
        for column in columns:
            with self.subTest(column=column):
                self.assertIn(f"<th>{column}</th>", self.index_source)
        self.assertIn('id="orchestra-model-table-body"', self.index_source)
        self.assertIn('id="orchestra-selection-count"', self.index_source)

    def test_user_saved_models_are_authoritative_for_orchestra_table(self) -> None:
        self.assertIn('jsonFetch("/api/orchestra/models")', self.app_source)
        self.assertIn("for (const model of state.orchestraModels)", self.app_source)
        self.assertNotIn("state.orchestraModels = uniqueModels", self.app_source)
        self.assertIn("Optional legacy presets", self.index_source)
        self.assertIn("never authoritative for the Orchestra selection table", self.index_source)

    def test_frontend_uses_all_bounded_configuration_and_live_routes(self) -> None:
        routes = (
            "/api/provider-connections",
            "/api/model-profiles",
            "/api/provider-connections/disable",
            "/api/model-profiles/disable",
            "/api/orchestra/models",
            "/api/provider-connections/test",
            "/api/orchestra/preview",
            "/api/orchestra/run",
        )
        for route in routes:
            with self.subTest(route=route):
                self.assertIn(f'"{route}"', self.app_source)

    def test_selection_validation_enforces_two_to_five_and_explicit_roles(self) -> None:
        self.assertIn("selections.length < 2 || selections.length > 5", self.app_source)
        self.assertIn("Exactly one selected model must be MAIN.", self.app_source)
        self.assertIn("Select at least one CRITIC or AUDITOR.", self.app_source)
        self.assertIn("Assign an explicit allowed role to every selected model.", self.app_source)
        self.assertIn("Roles are never changed automatically.", self.index_source)
        self.assertIn("const stageOrder = { MAIN: 0, CRITIC: 1, AUDITOR: 2, SYNTHESIZER: 3 };", self.app_source)

    def test_connection_test_requires_an_explicit_button_action(self) -> None:
        self.assertIn('actionButton("Test connection"', self.app_source)
        self.assertIn("async function testConnection(model)", self.app_source)
        self.assertIn("explicit_operator_action: true", self.app_source)
        refresh_function = self.app_source.split("async function refreshAll()", 1)[1].split(
            "for (const item of elements.navItems)", 1
        )[0]
        self.assertNotIn('jsonFetch("/api/provider-connections/test"', refresh_function)

    def test_plan_preview_cannot_enable_run_without_exact_confirmation(self) -> None:
        self.assertRegex(
            self.index_source,
            r'id="run-orchestra"[^>]*\bdisabled\b',
        )
        self.assertIn(
            "elements.orchestraConfirmationHash.value.trim() === state.orchestraPreviewHash",
            self.app_source,
        )
        self.assertIn("elements.orchestraConfirmPreview.checked", self.app_source)
        self.assertIn("Preview alone cannot authorize a call.", self.index_source)
        self.assertIn("explicit_run_action: true", self.app_source)

    def test_run_request_uses_confirmed_preview_and_does_not_resend_selection(self) -> None:
        run_function = self.app_source.split("async function runOrchestra()", 1)[1].split(
            "function renderSafeJson", 1
        )[0]
        self.assertIn("preview_hash: state.orchestraPreviewHash", run_function)
        self.assertIn("confirmation_hash: confirmationHash", run_function)
        self.assertNotIn("selections:", run_function)
        self.assertNotIn("model_profile_id:", run_function)

    def test_secret_values_are_not_rendered_and_live_output_is_bounded(self) -> None:
        self.assertIn("function safeUiPayload(value)", self.app_source)
        self.assertIn('safe[key] = "[REDACTED]";', self.app_source)
        self.assertIn("redactedError(error, apiKey)", self.app_source)
        self.assertIn("serialized.length > 12000", self.app_source)
        self.assertNotIn("localStorage", self.app_source)
        self.assertNotIn("sessionStorage", self.app_source)
        self.assertNotIn("console.log", self.app_source)
        self.assertIn("Provider output remains untrusted", self.index_source)
        self.assertIn("No fallback or automatic retry is permitted.", self.index_source)


if __name__ == "__main__":
    unittest.main()
