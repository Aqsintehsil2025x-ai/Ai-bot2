"""Security and ownership tests for XFA account storage."""
import base64
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from xfa_agent import accounts


class AccountStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp.name) / "xfa.sqlite3")
        self.key = base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")
        self.env = patch.dict(os.environ, {
            "XFA_DATABASE_PATH": self.db_path,
            "XFA_TOKEN_ENCRYPTION_KEY": self.key,
        })
        self.env.start()
        accounts.init_db()
        self.alice = accounts.create_user("Alice@example.com", "a-long-test-password")
        self.bob = accounts.create_user("bob@example.com", "another-long-password")

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_password_is_verified_without_storing_plaintext(self):
        self.assertEqual(
            accounts.verify_user("ALICE@example.com", "a-long-test-password")["id"],
            self.alice["id"],
        )
        self.assertIsNone(accounts.verify_user("alice@example.com", "incorrect-password"))
        with sqlite3.connect(self.db_path) as db:
            row = db.execute("SELECT password_salt,password_hash FROM xfa_users WHERE id=?",
                             (self.alice["id"],)).fetchone()
        self.assertNotIn(b"a-long-test-password", row[0] + row[1])

    def test_integrations_are_encrypted_and_user_scoped(self):
        saved = accounts.save_integration(
            self.alice["id"], "github", "gh-user-1", "ghp-secret-access",
            "ghr-secret-refresh", ["repo"], "Alice GitHub",
        )
        self.assertEqual(accounts.get_integration_tokens(self.alice["id"], saved["id"]), {
            "access_token": "ghp-secret-access",
            "refresh_token": "ghr-secret-refresh",
        })
        self.assertIsNone(accounts.get_integration_tokens(self.bob["id"], saved["id"]))
        self.assertEqual(accounts.list_integrations(self.bob["id"]), [])
        self.assertNotIn("access_token", accounts.list_integrations(self.alice["id"])[0])
        with sqlite3.connect(self.db_path) as db:
            encrypted = db.execute(
                "SELECT token_ciphertext FROM xfa_integrations WHERE id=?", (saved["id"],)
            ).fetchone()[0]
        self.assertNotIn(b"ghp-secret-access", encrypted)
        self.assertNotIn(b"ghr-secret-refresh", encrypted)

    def test_disconnect_cannot_delete_another_users_connection(self):
        saved = accounts.save_integration(
            self.alice["id"], "github", "gh-user-2", "access-token"
        )
        self.assertFalse(accounts.disconnect_integration(self.bob["id"], saved["id"]))
        self.assertTrue(accounts.disconnect_integration(self.alice["id"], saved["id"]))
        self.assertEqual(accounts.list_integrations(self.alice["id"]), [])

    def test_password_length_is_enforced(self):
        with self.assertRaises(ValueError):
            accounts.create_user("short@example.com", "tiny")


if __name__ == "__main__":
    unittest.main()
