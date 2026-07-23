from __future__ import annotations

import json
import unittest
from dataclasses import fields
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
from unittest.mock import patch

from apps.aoia_desktop_demo.state import settings as settings_module
from apps.aoia_desktop_demo.providers.openrouter import OPENROUTER_BASE_URL
from apps.aoia_desktop_demo.state.settings import DemoSettings, PROVIDER_CATALOG, SessionSecrets
from apps.aoia_desktop_demo.ui.settings_dialog import SettingsDialog


class NonSecretPersistenceTests(unittest.TestCase):
    def _with_temp_config(self, tmp_dir: str):
        config_dir = Path(tmp_dir) / "cfg"
        config_path = config_dir / "config.json"
        return patch.multiple(settings_module, CONFIG_DIR=config_dir, CONFIG_PATH=config_path)

    def test_no_api_key_field_exists_on_settings(self) -> None:
        field_names = {f.name for f in fields(DemoSettings)}
        for forbidden in ("api_key", "apikey", "secret", "token"):
            self.assertNotIn(forbidden, field_names)

    def test_save_and_load_roundtrip(self) -> None:
        with TemporaryDirectory() as tmp_dir, self._with_temp_config(tmp_dir):
            original = DemoSettings(
                provider="openrouter",
                api_base_url=OPENROUTER_BASE_URL,
                selected_model_id="openai/gpt-4.1-nano",
                knowledge_hat_id="german_federal_employment_worker_law",
                pre_delivery_critical_loop_enabled=True,
                observer_slots=[
                    {
                        "enabled": True,
                        "role": "Logic & Claims",
                        "provider_id": "openrouter",
                        "model_id": "google/gemma-3-4b-it",
                    },
                    {
                        "enabled": True,
                        "role": "Safety & Authority",
                        "provider_id": "openrouter",
                        "model_id": "anthropic/claude-3.5-haiku",
                    },
                    {
                        "enabled": True,
                        "role": "Evidence & Consistency",
                        "provider_id": "openrouter",
                        "model_id": "google/gemini-2.5-flash",
                    },
                ],
            )
            settings_module.save_settings(original)
            loaded = settings_module.load_settings()
            self.assertEqual(loaded.selected_model_id, "openai/gpt-4.1-nano")
            self.assertEqual(
                loaded.knowledge_hat_id,
                "german_federal_employment_worker_law",
            )
            self.assertEqual(loaded.observer_slots, original.observer_slots)
            self.assertTrue(loaded.pre_delivery_critical_loop_enabled)
            self.assertEqual(loaded.configured_provider_ids(), ("openrouter",))

    def test_malformed_observer_preferences_fail_closed(self) -> None:
        with TemporaryDirectory() as tmp_dir, self._with_temp_config(tmp_dir):
            settings_module.save_settings(DemoSettings())
            payload = json.loads(settings_module.CONFIG_PATH.read_text(encoding="utf-8"))
            payload["observer_slots"] = [
                {
                    "enabled": True,
                    "role": "Logic & Claims",
                    "provider_id": "openrouter",
                    "model_id": "not-a-model-id",
                }
            ]
            settings_module.CONFIG_PATH.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(settings_module.load_settings(), DemoSettings())

    def test_non_string_observer_role_fails_closed_without_crashing(self) -> None:
        with TemporaryDirectory() as tmp_dir, self._with_temp_config(tmp_dir):
            settings_module.save_settings(
                DemoSettings(
                    observer_slots=[
                        {
                            "enabled": True,
                            "role": role,
                            "provider_id": "openrouter",
                            "model_id": f"vendor/model-{index}",
                        }
                        for index, role in enumerate(
                            ("Logic & Claims", "Safety & Authority", "Evidence & Consistency"),
                            start=1,
                        )
                    ]
                )
            )
            payload = json.loads(settings_module.CONFIG_PATH.read_text(encoding="utf-8"))
            payload["observer_slots"][0]["role"] = []
            settings_module.CONFIG_PATH.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(settings_module.load_settings(), DemoSettings())

    def test_non_boolean_pre_delivery_mode_fails_closed(self) -> None:
        with TemporaryDirectory() as tmp_dir, self._with_temp_config(tmp_dir):
            settings_module.save_settings(DemoSettings())
            payload = json.loads(settings_module.CONFIG_PATH.read_text(encoding="utf-8"))
            payload["pre_delivery_critical_loop_enabled"] = "yes"
            settings_module.CONFIG_PATH.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(settings_module.load_settings(), DemoSettings())

    def test_saved_file_never_contains_key_shaped_content(self) -> None:
        with TemporaryDirectory() as tmp_dir, self._with_temp_config(tmp_dir):
            settings_module.save_settings(DemoSettings())
            raw_text = settings_module.CONFIG_PATH.read_text(encoding="utf-8")
            payload = json.loads(raw_text)
            for forbidden_key in ("api_key", "apiKey", "secret", "token", "authorization"):
                self.assertNotIn(forbidden_key, payload)
            self.assertNotIn("sk-", raw_text)

    def test_clear_settings_removes_file(self) -> None:
        with TemporaryDirectory() as tmp_dir, self._with_temp_config(tmp_dir):
            settings_module.save_settings(DemoSettings())
            self.assertTrue(settings_module.CONFIG_PATH.exists())
            settings_module.clear_settings()
            self.assertFalse(settings_module.CONFIG_PATH.exists())

    def test_load_settings_defaults_when_file_missing(self) -> None:
        with TemporaryDirectory() as tmp_dir, self._with_temp_config(tmp_dir):
            loaded = settings_module.load_settings()
            self.assertEqual(loaded, DemoSettings())

    def test_load_settings_ignores_unexpected_keys(self) -> None:
        with TemporaryDirectory() as tmp_dir, self._with_temp_config(tmp_dir):
            settings_module.save_settings(DemoSettings())
            payload = json.loads(settings_module.CONFIG_PATH.read_text(encoding="utf-8"))
            payload.update({"selected_model_id": "openai/gpt-4.1-nano", "api_key": "should-be-ignored"})
            settings_module.CONFIG_PATH.write_text(json.dumps(payload), encoding="utf-8")
            loaded = settings_module.load_settings()
            self.assertEqual(loaded.selected_model_id, "openai/gpt-4.1-nano")
            self.assertFalse(hasattr(loaded, "api_key"))

    def test_fresh_start_has_no_configured_connections_or_active_model(self) -> None:
        fresh = DemoSettings()
        self.assertEqual(fresh.configured_provider_ids(), ())
        self.assertEqual(fresh.provider, "")
        self.assertEqual(fresh.api_base_url, "")
        self.assertEqual(fresh.manual_model_id, "")
        self.assertEqual(fresh.selected_model_id, "")

    def test_provider_catalog_is_not_a_configured_connection(self) -> None:
        self.assertEqual(PROVIDER_CATALOG, ("openrouter",))
        self.assertEqual(DemoSettings().configured_provider_ids(), ())

    def test_legacy_seeded_settings_are_removed_once_and_do_not_reappear(self) -> None:
        with TemporaryDirectory() as tmp_dir, self._with_temp_config(tmp_dir):
            settings_module.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            settings_module.CONFIG_PATH.write_text(
                json.dumps(
                    {
                        "provider": "openrouter",
                        "api_base_url": OPENROUTER_BASE_URL,
                        "manual_model_id": "openai/gpt-4.1-nano",
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(settings_module.load_settings(), DemoSettings())
            self.assertFalse(settings_module.CONFIG_PATH.exists())
            self.assertEqual(settings_module.load_settings(), DemoSettings())

    def test_operator_created_configuration_survives_restart(self) -> None:
        with TemporaryDirectory() as tmp_dir, self._with_temp_config(tmp_dir):
            operator_settings = DemoSettings(
                provider="openrouter",
                api_base_url=OPENROUTER_BASE_URL,
                manual_model_id="openai/gpt-4.1-nano",
            )
            settings_module.save_settings(operator_settings)
            restored = settings_module.load_settings()
            self.assertEqual(restored.configured_provider_ids(), ("openrouter",))
            self.assertEqual(restored.manual_model_id, "openai/gpt-4.1-nano")

    def test_schema_two_none_migrates_to_none_without_enabling_a_hat(self) -> None:
        with TemporaryDirectory() as tmp_dir, self._with_temp_config(tmp_dir):
            settings_module.CONFIG_DIR.mkdir(parents=True)
            settings_module.CONFIG_PATH.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "operator_created": True,
                        "knowledge_profile_id": "none",
                    }
                ),
                encoding="utf-8",
            )
            loaded = settings_module.load_settings()
            self.assertEqual(loaded.knowledge_hat_id, "none")
            self.assertEqual(loaded.knowledge_hat_configuration_notice, "")

    def test_legacy_enabled_profile_never_auto_migrates_to_german_hat(self) -> None:
        with TemporaryDirectory() as tmp_dir, self._with_temp_config(tmp_dir):
            settings_module.CONFIG_DIR.mkdir(parents=True)
            settings_module.CONFIG_PATH.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "operator_created": True,
                        "knowledge_profile_id": "linux_unix",
                    }
                ),
                encoding="utf-8",
            )
            loaded = settings_module.load_settings()
            self.assertEqual(loaded.knowledge_hat_id, "none")
            self.assertIn("unavailable", loaded.knowledge_hat_configuration_notice)

    def test_unknown_or_malformed_hat_selection_resolves_visibly_to_none(self) -> None:
        for selected in ("unknown_hat", ["malformed"]):
            with self.subTest(selected=selected), TemporaryDirectory() as tmp_dir, self._with_temp_config(tmp_dir):
                settings_module.CONFIG_DIR.mkdir(parents=True)
                settings_module.CONFIG_PATH.write_text(
                    json.dumps(
                        {
                            "schema_version": settings_module.CONFIG_SCHEMA_VERSION,
                            "operator_created": True,
                            "knowledge_hat_id": selected,
                        }
                    ),
                    encoding="utf-8",
                )
                loaded = settings_module.load_settings()
                self.assertEqual(loaded.knowledge_hat_id, "none")
                self.assertIn("unavailable", loaded.knowledge_hat_configuration_notice)

    def test_fresh_settings_require_explicit_hat_enablement(self) -> None:
        self.assertEqual(DemoSettings().knowledge_hat_id, "none")

    def test_malformed_or_incomplete_records_stay_inactive(self) -> None:
        incomplete = DemoSettings(provider="openrouter", api_base_url=OPENROUTER_BASE_URL)
        malformed = DemoSettings(
            provider="openrouter", api_base_url=OPENROUTER_BASE_URL, manual_model_id="not a model identifier"
        )
        self.assertEqual(incomplete.configured_provider_ids(), ())
        self.assertEqual(malformed.configured_provider_ids(), ())

    def test_manual_openrouter_form_values_can_be_stored(self) -> None:
        dialog = object.__new__(SettingsDialog)
        settings = DemoSettings()
        dialog.controller = SimpleNamespace(settings=settings)
        dialog.provider_var = SimpleNamespace(get=lambda: "OpenRouter")
        dialog.base_url_var = SimpleNamespace(get=lambda: OPENROUTER_BASE_URL)
        dialog.app_title_var = SimpleNamespace(get=lambda: "AOIA Control Chat Competition Demo")
        dialog.timeout_var = SimpleNamespace(get=lambda: "30")
        dialog.manual_model_var = SimpleNamespace(get=lambda: "openai/gpt-4.1-nano")
        dialog.max_tokens_var = SimpleNamespace(get=lambda: "")
        dialog._apply_non_secret_fields()
        self.assertEqual(settings.provider, "openrouter")
        self.assertEqual(settings.api_base_url, OPENROUTER_BASE_URL)
        self.assertEqual(settings.manual_model_id, "openai/gpt-4.1-nano")
        self.assertEqual(settings.configured_provider_ids(), ("openrouter",))


class SessionSecretsTests(unittest.TestCase):
    def test_no_api_key_is_part_of_fresh_or_serialized_state(self) -> None:
        fresh = DemoSettings()
        self.assertNotIn("api_key", fresh.to_json_dict())
        self.assertNotIn("apiKey", fresh.to_json_dict())

    def test_repr_never_includes_key_value(self) -> None:
        secrets = SessionSecrets(api_key="super-secret-value")
        self.assertNotIn("super-secret-value", repr(secrets))

    def test_clear_removes_key(self) -> None:
        secrets = SessionSecrets(api_key="x")
        secrets.clear()
        self.assertIsNone(secrets.api_key)
        self.assertEqual(secrets.source, "none")

    def test_set_for_session_updates_source(self) -> None:
        secrets = SessionSecrets()
        secrets.set_for_session("sk-or-test-redacted")
        self.assertEqual(secrets.source, "session-entry")
        self.assertNotIn("sk-or-test-redacted", repr(secrets))
        secrets.set_for_session("")
        self.assertEqual(secrets.source, "none")
        self.assertIsNone(secrets.api_key)


if __name__ == "__main__":
    unittest.main()
