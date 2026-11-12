import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from flask import Flask
from itsdangerous import URLSafeTimedSerializer

from xfa_agent.auth import register_auth
from xfa_agent.routes import register_xfa
from xfa_agent.accounts import create_user


class XFAAuthSmokeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_env = {
            key: os.environ.get(key)
            for key in ("FLASK_SECRET_KEY", "XFA_DATABASE_PATH", "XFA_COOKIE_SECURE")
        }
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

    def test_api_requires_google_or_discord_login(self):
        response = self.client.get("/xfa/api/health")
        self.assertEqual(response.status_code, 401)

    def test_session_cookie_is_opaque_and_server_side(self):
        self._login_test_session()
        cookie = self.client.get_cookie("xfa_session")
        self.assertIsNotNone(cookie)
        self.assertTrue(cookie.http_only)
        self.assertTrue(cookie.secure)
        self.assertEqual(cookie.same_site, "Lax")
        sid = URLSafeTimedSerializer(
            self.app.secret_key, salt="xfa-server-session-v1"
        ).loads(cookie.value)
        db_path = Path(self.temp_dir.name) / "xfa.sqlite3"
        with sqlite3.connect(db_path) as db:
            row = db.execute("SELECT data FROM xfa_sessions WHERE sid=?", (sid,)).fetchone()
        self.assertIsNotNone(row)
        self.assertIn(self.user["id"], row[0])
        self.assertNotIn(self.user["id"], cookie.value)
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
        self.assertEqual(allowed_through_csrf.status_code, 503)

    def test_auth_me_reports_authenticated_profile(self):
        self._login_test_session()
        with sqlite3.connect(Path(self.temp_dir.name) / "auth.sqlite3") as db:
            db.execute(
                "INSERT INTO users(id, display_name, email, created_at) VALUES(?,?,?,?)",
                ("test-user-01", "Test User", "test@example.invalid", 1),
            )
        response = self.client.get("/auth/me")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["authenticated"])
        self.assertEqual(response.json["user"]["name"], "Test User")
        self.assertEqual(response.json["csrf_token"], "csrf-test-value")


if __name__ == "__main__":
    unittest.main()
