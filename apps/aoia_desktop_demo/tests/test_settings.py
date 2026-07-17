from __future__ import annotations

import json
import os
import unittest
from dataclasses import fields
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from apps.aoia_desktop_demo.state import settings as settings_module
from apps.aoia_desktop_demo.state.settings import DemoSettings, SessionSecrets


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
            original = DemoSettings(selected_model_id="vendor/model-x", knowledge_profile_id="linux_unix")
            settings_module.save_settings(original)
            loaded = settings_module.load_settings()
            self.assertEqual(loaded.selected_model_id, "vendor/model-x")
            self.assertEqual(loaded.knowledge_profile_id, "linux_unix")

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
            settings_module.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            settings_module.CONFIG_PATH.write_text(
                json.dumps({"selected_model_id": "vendor/x", "api_key": "should-be-ignored"}),
                encoding="utf-8",
            )
            loaded = settings_module.load_settings()
            self.assertEqual(loaded.selected_model_id, "vendor/x")
            self.assertFalse(hasattr(loaded, "api_key"))


class SessionSecretsTests(unittest.TestCase):
    def test_from_environment_reads_but_does_not_persist(self) -> None:
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "env-key-value"}, clear=False):
            secrets = SessionSecrets.from_environment()
            self.assertEqual(secrets.api_key, "env-key-value")
            self.assertEqual(secrets.source, "environment")

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
        secrets.set_for_session("abc")
        self.assertEqual(secrets.source, "session-entry")
        secrets.set_for_session("")
        self.assertEqual(secrets.source, "none")
        self.assertIsNone(secrets.api_key)


if __name__ == "__main__":
    unittest.main()
