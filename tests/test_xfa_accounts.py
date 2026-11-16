"""Security and ownership tests for XFA account storage."""
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
        self.env = patch.dict(os.environ, {
            "XFA_DATABASE_PATH": self.db_path,
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

    def test_legacy_personal_api_key_storage_is_removed(self):
        with sqlite3.connect(self.db_path) as db:
            tables = {
                row[0] for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        self.assertNotIn("xfa_integrations", tables)

    def test_password_length_is_enforced(self):
        with self.assertRaises(ValueError):
            accounts.create_user("short@example.com", "tiny")


if __name__ == "__main__":
    unittest.main()
