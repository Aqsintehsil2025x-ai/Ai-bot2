import os
import unittest
from unittest.mock import patch

from xfa_agent.providers import (
    PROVIDERS,
    _safe_provider_error,
    _status_code,
    public_catalog,
    server_api_key,
)


class XFAProviderConfigTests(unittest.TestCase):
    def test_gemini_default_is_current_catalog_model(self):
        self.assertEqual(PROVIDERS["gemini"]["default_model"], "gemini-3.5-flash-lite")
        self.assertIn(PROVIDERS["gemini"]["default_model"], PROVIDERS["gemini"]["models"])
        self.assertIn("gemini-3.8-flash", PROVIDERS["gemini"]["models"])
        self.assertNotIn("gemini-2.0-flash", PROVIDERS["gemini"]["models"])
        self.assertNotIn("gemini-2.5-flash", PROVIDERS["gemini"]["models"])

    def test_nvidia_default_is_in_catalog(self):
        self.assertEqual(
            PROVIDERS["nvidia"]["default_model"],
            "meta/llama-3.3-70b-instruct",
        )
        self.assertIn(
            PROVIDERS["nvidia"]["default_model"],
            PROVIDERS["nvidia"]["models"],
        )

    def test_public_catalog_does_not_expose_credentials(self):
        catalog = public_catalog()
        self.assertEqual(set(catalog), {"gemini", "nvidia"})
        self.assertNotIn("api_key", str(catalog).lower())
        self.assertNotIn("base_url", catalog["nvidia"])

    def test_gemini_uses_google_api_key_as_fallback(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "fallback-test"}, clear=False):
            self.assertEqual(server_api_key("gemini"), "fallback-test")

    def test_provider_errors_are_sanitized_and_actionable(self):
        self.assertIn("model", _safe_provider_error(404).lower())
        self.assertIn("icazə", _safe_provider_error(403).lower())
        self.assertIn("limit", _safe_provider_error(429).lower())
        self.assertNotIn("secret", _safe_provider_error(404).lower())

    def test_status_code_extraction(self):
        class ProviderError(Exception):
            status_code = 404

        self.assertEqual(_status_code(ProviderError("not found")), 404)
        self.assertIsNone(_status_code(RuntimeError("unknown")))


if __name__ == "__main__":
    unittest.main()
