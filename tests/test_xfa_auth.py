import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from flask import Flask

from xfa_agent.auth import register_auth
from xfa_agent.routes import register_xfa
from xfa_agent.accounts import create_user


class XFAAuthSmokeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_env = {
            key: os.environ.get(key)
            for key in ("FLASK_SECRET_KEY", "XFA_DATABASE_PATH", "XFA_COOKIE_SECURE", "GEMINI_API_KEY", "GOOGLE_API_KEY", "NVIDIA_API_KEY")
        }
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("GOOGLE_API_KEY", None)
        os.environ.pop("NVIDIA_API_KEY", None)
        os.environ["FLASK_SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-tests"
        os.environ["XFA_DATABASE_PATH"] = str(Path(self.temp_dir.name) / "xfa.sqlite3")
        os.environ["XFA_COOKIE_SECURE"] = "true"

        app = Flask(__name__)
        app.testing = True
        register_auth(app)
        register_xfa(app)
        self.app = app
        self.client = app.test_client()
        self.user = create_user("test@example.invalid", "a-random-test-password-123")

    def tearDown(self):
        for key, value in self.old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.temp_dir.cleanup()

    def _login_test_session(self):
        with self.client.session_transaction() as sess:
            sess["xfa_user_id"] = self.user["id"]
            sess["xfa_display_name"] = "Test User"
            sess["xfa_email"] = "test@example.invalid"
            sess["xfa_csrf"] = "csrf-test-value"
            sess.permanent = True

    def test_auth_provider_readiness_does_not_expose_secrets(self):
        response = self.client.get("/auth/providers")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["session_ready"])
        self.assertFalse(response.json["google"])
        self.assertNotIn("discord", response.json)
        self.assertNotIn("client_secret", response.json)

    def test_api_requires_google_login(self):
        response = self.client.get("/xfa/api/health")
        self.assertEqual(response.status_code, 401)

    def test_discord_oauth_is_disabled(self):
        response = self.client.get("/auth/login/discord")
        self.assertEqual(response.status_code, 404)

    def test_session_uses_flask_signed_secure_cookie_without_session_database(self):
        self._login_test_session()
        cookie = self.client.get_cookie("xfa_session")
        self.assertIsNotNone(cookie)
        self.assertTrue(cookie.http_only)
        self.assertTrue(cookie.secure)
        self.assertEqual(cookie.same_site, "Lax")
        serializer = self.app.session_interface.get_signing_serializer(self.app)
        payload = serializer.loads(cookie.value)
        self.assertEqual(payload["xfa_user_id"], self.user["id"])
        db_path = Path(self.temp_dir.name) / "xfa.sqlite3"
        with sqlite3.connect(db_path) as db:
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertNotIn("xfa_sessions", tables)
        self.assertEqual(self.client.get("/xfa/api/health").status_code, 200)

    def test_api_post_requires_csrf_header(self):
        self._login_test_session()
        denied = self.client.post("/xfa/api/tasks/plan", json={"task": "test"})
        self.assertEqual(denied.status_code, 403)
        allowed_through_csrf = self.client.post(
            "/xfa/api/tasks/plan",
            json={"task": "test"},
            headers={"X-CSRF-Token": "csrf-test-value"},
        )
        # No model API key is configured in this test, so authentication/CSRF
        # succeeds and the endpoint then reports that the planner is unavailable.
        self.assertEqual(allowed_through_csrf.status_code, 400)

    def test_provider_catalog_uses_only_server_managed_gemini_and_nvidia(self):
        self._login_test_session()
        os.environ["GEMINI_API_KEY"] = "server-gemini-secret"
        os.environ["NVIDIA_API_KEY"] = "server-nvidia-secret"
        response = self.client.get("/xfa/api/providers")
        self.assertEqual(response.status_code, 200)
        providers = response.json["connected"]
        self.assertEqual({item["id"] for item in providers}, {"gemini", "nvidia"})
        self.assertTrue(all(item["connected"] for item in providers))
        body = response.get_data(as_text=True)
        self.assertNotIn("server-gemini-secret", body)
        self.assertNotIn("server-nvidia-secret", body)
        self.assertNotIn("groq", body)

    def test_google_api_key_is_supported_as_gemini_fallback(self):
        self._login_test_session()
        os.environ["GOOGLE_API_KEY"] = "google-fallback-secret"
        response = self.client.get("/xfa/api/providers")
        self.assertEqual(response.status_code, 200)
        gemini = next(item for item in response.json["connected"] if item["id"] == "gemini")
        self.assertTrue(gemini["connected"])
        self.assertNotIn("google-fallback-secret", response.get_data(as_text=True))

    def test_provider_catalog_selects_nvidia_when_it_is_the_only_server_key(self):
        self._login_test_session()
        os.environ["NVIDIA_API_KEY"] = "server-nvidia-secret"
        response = self.client.get("/xfa/api/providers")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["active"], "nvidia")
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["xfa_ai_provider"], "nvidia")
            self.assertEqual(sess["xfa_ai_model"], "meta/llama-3.3-70b-instruct")

    def test_provider_selection_requires_server_secret(self):
        self._login_test_session()
        headers = {"X-CSRF-Token": "csrf-test-value"}
        missing = self.client.post(
            "/xfa/api/providers/select",
            json={"provider": "nvidia", "model": "meta/llama-3.3-70b-instruct"},
            headers=headers,
        )
        self.assertEqual(missing.status_code, 503)
        os.environ["NVIDIA_API_KEY"] = "server-nvidia-secret"
        selected = self.client.post(
            "/xfa/api/providers/select",
            json={"provider": "nvidia", "model": "meta/llama-3.3-70b-instruct"},
            headers=headers,
        )
        self.assertEqual(selected.status_code, 200)
        self.assertEqual(selected.json["provider"], "nvidia")

    def test_chat_uses_server_managed_api_key(self):
        self._login_test_session()
        os.environ["GEMINI_API_KEY"] = "server-gemini-secret"
        from unittest.mock import patch
        with patch("xfa_agent.providers.generate", return_value="Hello from XFA") as generate:
            response = self.client.post(
                "/xfa/api/chat",
                json={"messages": [{"role": "user", "content": "Hello"}],
                      "provider": "gemini", "model": "gemini-3.8-flash"},
                headers={"X-CSRF-Token": "csrf-test-value"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["reply"], "Hello from XFA")
        self.assertEqual(generate.call_args.args[0:3],
                         ("gemini", "server-gemini-secret", "gemini-3.8-flash"))

    def test_personal_api_key_management_routes_are_removed(self):
        self._login_test_session()
        headers = {"X-CSRF-Token": "csrf-test-value"}
        self.assertEqual(self.client.post("/xfa/api/providers", json={}, headers=headers).status_code, 405)
        self.assertEqual(self.client.post("/xfa/api/providers/test", json={}, headers=headers).status_code, 404)
        self.assertEqual(self.client.delete("/xfa/api/providers/groq", headers=headers).status_code, 404)

    def test_anonymous_auth_me_issues_csrf_token(self):
        response = self.client.get("/auth/me")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json["authenticated"])
        self.assertTrue(response.json["csrf_token"])

    def test_email_registration_and_password_login(self):
        anonymous = self.client.get("/auth/me")
        csrf = anonymous.json["csrf_token"]
        registered = self.client.post(
            "/auth/register",
            json={"email": "new-user@example.invalid", "password": "a-strong-test-password-123"},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(registered.status_code, 200)
        self.assertTrue(registered.json["ok"])
        profile = self.client.get("/auth/me")
        self.assertTrue(profile.json["authenticated"])
        self.assertEqual(profile.json["user"]["email"], "new-user@example.invalid")
        self.assertEqual(profile.json["csrf_token"] != csrf, True)

        self.client.post(
            "/auth/logout",
            headers={"X-CSRF-Token": profile.json["csrf_token"]},
        )
        anonymous_again = self.client.get("/auth/me")
        login = self.client.post(
            "/auth/login/password",
            json={"email": "NEW-USER@example.invalid", "password": "a-strong-test-password-123"},
            headers={"X-CSRF-Token": anonymous_again.json["csrf_token"]},
        )
        self.assertEqual(login.status_code, 200)
        self.assertTrue(self.client.get("/auth/me").json["authenticated"])

    def test_password_auth_rejects_invalid_password_and_csrf(self):
        anonymous = self.client.get("/auth/me")
        csrf = anonymous.json["csrf_token"]
        no_csrf = self.client.post(
            "/auth/register",
            json={"email": "another@example.invalid", "password": "a-strong-test-password-123"},
        )
        self.assertEqual(no_csrf.status_code, 403)
        weak_password = self.client.post(
            "/auth/register",
            json={"email": "another@example.invalid", "password": "short"},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(weak_password.status_code, 400)
        bad_login = self.client.post(
            "/auth/login/password",
            json={"email": "test@example.invalid", "password": "incorrect-password-123"},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(bad_login.status_code, 401)
        self.assertEqual(bad_login.json["error"], "E-posta veya parola hatalı.")

    def test_duplicate_email_registration_is_rejected(self):
        anonymous = self.client.get("/auth/me")
        response = self.client.post(
            "/auth/register",
            json={"email": "TEST@example.invalid", "password": "a-strong-test-password-123"},
            headers={"X-CSRF-Token": anonymous.json["csrf_token"]},
        )
        self.assertEqual(response.status_code, 409)

    def test_auth_me_reports_authenticated_profile(self):
        self._login_test_session()
        response = self.client.get("/auth/me")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["authenticated"])
        self.assertEqual(response.json["user"]["name"], "Test User")
        self.assertEqual(response.json["csrf_token"], "csrf-test-value")


if __name__ == "__main__":
    unittest.main()
