import base64
import os
import secrets
import tempfile
import unittest
from pathlib import Path

from flask import Flask

from xfa_agent.accounts import create_user
from xfa_agent.auth import register_auth
from xfa_agent.routes import register_xfa


class XFAMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_env = {
            key: os.environ.get(key)
            for key in ("FLASK_SECRET_KEY", "XFA_DATABASE_PATH", "XFA_COOKIE_SECURE", "XFA_TOKEN_ENCRYPTION_KEY")
        }
        os.environ["FLASK_SECRET_KEY"] = "test-secret-key-for-memory-tests"
        os.environ["XFA_DATABASE_PATH"] = str(Path(self.temp_dir.name) / "xfa.sqlite3")
        os.environ["XFA_COOKIE_SECURE"] = "false"
        os.environ["XFA_TOKEN_ENCRYPTION_KEY"] = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")
        app = Flask(__name__)
        app.testing = True
        register_auth(app)
        register_xfa(app)
        self.client = app.test_client()
        self.user = create_user("memory@example.invalid", "test-password-123456")
        self.other = create_user("other@example.invalid", "other-password-123456")
        with self.client.session_transaction() as sess:
            sess["xfa_user_id"] = self.user["id"]
            sess["xfa_csrf"] = "memory-csrf"
            sess.permanent = True

    def tearDown(self):
        for key, value in self.old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.temp_dir.cleanup()

    def test_memory_crud_and_account_isolation(self):
        headers = {"X-CSRF-Token": "memory-csrf"}
        created = self.client.post(
            "/xfa/api/memory",
            json={"title": "XFA preference", "content": "Use Turkish UI", "tags": ["ui", "turkish"]},
            headers=headers,
        )
        self.assertEqual(created.status_code, 201)
        item = created.json["item"]
        self.assertEqual(item["content"], "Use Turkish UI")
        self.assertEqual(item["tags"], ["turkish", "ui"])

        from xfa_agent.memory import list_memories
        self.assertEqual(len(list_memories(self.user["id"])), 1)
        self.assertEqual(list_memories(self.other["id"]), [])

        updated = self.client.put(
            "/xfa/api/memory/" + item["id"],
            json={"title": "Updated", "content": "Changed"},
            headers=headers,
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json["item"]["title"], "Updated")

        self.assertEqual(self.client.get("/xfa/api/memory?q=Changed").json["items"][0]["id"], item["id"])
        deleted = self.client.delete("/xfa/api/memory/" + item["id"], headers=headers)
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(self.client.get("/xfa/api/memory").json["items"], [])

    def test_memory_requires_csrf_and_rejects_empty_content(self):
        denied = self.client.post("/xfa/api/memory", json={"title": "x", "content": "y"})
        self.assertEqual(denied.status_code, 403)
        invalid = self.client.post(
            "/xfa/api/memory",
            json={"title": "   ", "content": "text"},
            headers={"X-CSRF-Token": "memory-csrf"},
        )
        self.assertEqual(invalid.status_code, 400)

    def test_memory_item_cannot_be_updated_or_deleted_by_another_user(self):
        from xfa_agent.memory import create_memory, update_memory, delete_memory
        item = create_memory(self.user["id"], "Private", "Only my account")
        self.assertIsNone(update_memory(self.other["id"], item["id"], "Hijack", "No"))
        self.assertFalse(delete_memory(self.other["id"], item["id"]))
        self.assertEqual(len(list_memories(self.user["id"])), 1)


if __name__ == "__main__":
    unittest.main()
