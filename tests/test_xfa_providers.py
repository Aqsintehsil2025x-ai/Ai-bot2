import os
import unittest
from unittest.mock import patch

from xfa_agent.providers import (
    PROVIDERS,
    _safe_provider_error,
    _status_code,
    public_catalog,
    server_api_key,
    _normalize_openai_messages,
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

    def test_nvidia_history_drops_display_only_leading_greeting(self):
        messages = _normalize_openai_messages([
            {"role": "model", "content": "Merhaba! Ben XFA."},
            {"role": "user", "content": "Salam"},
            {"role": "model", "content": "Salam!"},
            {"role": "user", "content": "Necəsən?"},
        ])
        self.assertEqual(
            messages,
            [
                {"role": "user", "content": "Salam"},
                {"role": "assistant", "content": "Salam!"},
                {"role": "user", "content": "Necəsən?"},
            ],
        )

    def test_nvidia_history_merges_repeated_roles_and_ends_with_user(self):
        messages = _normalize_openai_messages([
            {"role": "model", "content": "Display greeting"},
            {"role": "user", "content": "Birinci hissə"},
            {"role": "user", "content": "İkinci hissə"},
            {"role": "model", "content": "Cavab"},
        ])
        self.assertEqual(messages, [{"role": "user", "content": "Birinci hissə\n\nİkinci hissə"}])

    def test_nvidia_history_requires_a_user_message(self):
        with self.assertRaises(ValueError):
            _normalize_openai_messages([
                {"role": "model", "content": "Only greeting"},
            ])

    def test_public_catalog_does_not_expose_credentials(self):
        catalog = public_catalog()
        self.assertEqual(set(catalog), {"gemini", "nvidia", "groq", "openrouter", "deepseek"})
        self.assertNotIn("api_key", str(catalog).lower())
        for provider in catalog.values():
            self.assertNotIn("base_url", provider)
        self.assertEqual(catalog["openrouter"]["default_model"], "openrouter/free")
        self.assertEqual(catalog["deepseek"]["default_model"], "deepseek-flash")

    def test_gemini_uses_google_api_key_as_fallback(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "fallback-test"}, clear=False):
            self.assertEqual(server_api_key("gemini"), "fallback-test")

    def test_additional_server_keys_are_provider_scoped(self):
        values = {
            "GROQ_API_KEY": "groq-test",
            "OPENROUTER_API_KEY": "router-test",
            "DEEPSEEK_API_KEY": "deepseek-test",
        }
        with patch.dict(os.environ, values, clear=False):
            self.assertEqual(server_api_key("groq"), "groq-test")
            self.assertEqual(server_api_key("openrouter"), "router-test")
            self.assertEqual(server_api_key("deepseek"), "deepseek-test")
        self.assertEqual(server_api_key("unknown"), "")

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
