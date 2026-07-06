from __future__ import annotations

import unittest
from unittest.mock import patch

from runtime.provider_config import (
    get_provider_config_status,
    is_gemini_configured,
    is_kimi_configured,
    is_openrouter_configured,
)


class ProviderConfigTests(unittest.TestCase):
    def test_missing_keys_return_false(self) -> None:
        with patch.dict("os.environ", {}, clear=True), patch("runtime.provider_config._read_key_file", return_value=None):
            self.assertFalse(is_gemini_configured())
            self.assertFalse(is_kimi_configured())
            self.assertFalse(is_openrouter_configured())
            self.assertEqual(
                {
                    "gemini_configured": False,
                    "kimi_configured": False,
                    "openrouter_configured": False,
                },
                get_provider_config_status(),
            )

    def test_mocked_keys_return_true_without_exposing_values(self) -> None:
        secret_values = {
            "GEMINI_API_KEY": "gemini-secret-value",
            "KIMI_API_KEY": "kimi-secret-value",
            "OPENROUTER_API_KEY": "openrouter-secret-value",
        }
        with patch.dict("os.environ", secret_values, clear=True):
            status = get_provider_config_status()

        self.assertEqual(
            {"gemini_configured": True, "kimi_configured": True, "openrouter_configured": True},
            status,
        )
        self.assertTrue(all(isinstance(value, bool) for value in status.values()))
        self.assertNotIn("gemini-secret-value", repr(status))
        self.assertNotIn("kimi-secret-value", repr(status))
        self.assertNotIn("openrouter-secret-value", repr(status))
        self.assertNotIn("GEMINI_API_KEY", status)
        self.assertNotIn("KIMI_API_KEY", status)
        self.assertNotIn("OPENROUTER_API_KEY", status)


if __name__ == "__main__":
    unittest.main()
