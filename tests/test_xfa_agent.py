import base64
import os
import secrets
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask

from xfa_agent.accounts import create_user, save_integration
from xfa_agent.auth import register_auth
from xfa_agent.routes import register_xfa


class XFAAgentRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_env = {
            key: os.environ.get(key)
            for key in ("FLASK_SECRET_KEY", "XFA_DATABASE_PATH", "XFA_COOKIE_SECURE", "XFA_TOKEN_ENCRYPTION_KEY")
        }
        os.environ["FLASK_SECRET_KEY"] = "test-secret-key-for-agent-tests"
        os.environ["XFA_DATABASE_PATH"] = str(Path(self.temp_dir.name) / "xfa.sqlite3")
        os.environ["XFA_COOKIE_SECURE"] = "false"
        os.environ["XFA_TOKEN_ENCRYPTION_KEY"] = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")
        app = Flask(__name__)
        app.testing = True
        register_auth(app)
        register_xfa(app)
        self.client = app.test_client()
        self.user = create_user("agent@example.invalid", "agent-test-password-123")
        save_integration(
            self.user["id"], "ai_provider", "groq", "test-provider-secret",
            display_name="openai/gpt-oss-120b",
        )
        with self.client.session_transaction() as sess:
            sess["xfa_user_id"] = self.user["id"]
            sess["xfa_csrf"] = "agent-csrf"
            sess["xfa_ai_provider"] = "groq"
            sess["xfa_ai_model"] = "openai/gpt-oss-120b"
            sess.permanent = True

    def tearDown(self):
        for key, value in self.old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.temp_dir.cleanup()

    def test_research_agent_uses_selected_provider_and_returns_sources(self):
        search_results = [{
            "title": "Example source",
            "url": "https://example.com/article",
            "snippet": "Grounded information.",
        }]
        with patch(
            "xfa_agent.providers.generate",
            side_effect=[
                '{"action":"search","query":"test query"}',
                '{"action":"finish","answer":"A grounded answer [1]."}',
            ],
        ) as generate, patch(
            "xfa_agent.web_search.search_public_web",
            return_value=search_results,
        ):
            response = self.client.post(
                "/xfa/api/tasks/run",
                json={"task": "Research a test topic"},
                headers={"X-CSRF-Token": "agent-csrf"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["provider"], "groq")
        self.assertEqual(response.json["sources"][0]["url"], "https://example.com/article")
        self.assertIn("[1]", response.json["answer"])
        self.assertEqual(generate.call_count, 2)

    def test_research_agent_requires_csrf(self):
        response = self.client.post("/xfa/api/tasks/run", json={"task": "Research"})
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
