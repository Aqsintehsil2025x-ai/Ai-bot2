import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from xfa_agent import workspace


class WorkspaceSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.root.joinpath("README.md").write_text("hello", encoding="utf-8")
        self.original_pending = dict(workspace._pending)
        workspace._pending.clear()
        self.root_patch = patch.object(workspace, "ROOT", self.root)
        self.root_patch.start()

    def tearDown(self):
        self.root_patch.stop()
        workspace._pending.clear()
        workspace._pending.update(self.original_pending)
        self.temp.cleanup()

    def test_reads_file_inside_workspace(self):
        self.assertEqual(workspace.read_file("README.md")["content"], "hello")

    def test_rejects_parent_traversal(self):
        with self.assertRaises(ValueError):
            workspace.read_file("../outside.txt")

    def test_rejects_absolute_paths(self):
        with self.assertRaises(ValueError):
            workspace.read_file(str(self.root / "README.md"))

    def test_rejects_hidden_and_secret_paths(self):
        for path in (".env", ".git/config", "folder/.hidden", "cookies.txt"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                workspace._safe_path(path)

    def test_listing_skips_hidden_and_dependency_directories(self):
        (self.root / ".git").mkdir()
        (self.root / "node_modules").mkdir()
        (self.root / "visible").mkdir()
        names = {item["name"] for item in workspace.list_files(".")}
        self.assertEqual(names, {"README.md", "visible"})

    def test_new_file_requires_approval_and_never_overwrites(self):
        approval_id = workspace.propose_new_file("notes/agent.md", "draft")
        self.assertFalse((self.root / "notes/agent.md").exists())
        result = workspace.approve_new_file(approval_id)
        self.assertEqual(result["path"], "notes/agent.md")
        self.assertEqual((self.root / "notes/agent.md").read_text(encoding="utf-8"), "draft")
        with self.assertRaises(ValueError):
            workspace.propose_new_file("README.md", "replacement")

    def test_expired_approval_is_rejected(self):
        approval_id = workspace.propose_new_file("notes/expired.md", "draft")
        workspace._pending[approval_id]["expires"] = 0
        with self.assertRaises(ValueError):
            workspace.approve_new_file(approval_id)

    def test_existing_file_update_requires_approval(self):
        approval_id = workspace.propose_update_file("README.md", "updated")
        self.assertEqual((self.root / "README.md").read_text(encoding="utf-8"), "hello")
        result = workspace.approve_new_file(approval_id)
        self.assertEqual(result["operation"], "updated")
        self.assertEqual((self.root / "README.md").read_text(encoding="utf-8"), "updated")

    def test_stale_update_is_rejected(self):
        approval_id = workspace.propose_update_file("README.md", "updated")
        (self.root / "README.md").write_text("changed elsewhere", encoding="utf-8")
        with self.assertRaises(ValueError):
            workspace.approve_new_file(approval_id)
        self.assertEqual((self.root / "README.md").read_text(encoding="utf-8"), "changed elsewhere")

    def test_disallowed_file_type_is_rejected(self):
        with self.assertRaises(ValueError):
            workspace.propose_new_file("run.sh", "echo unsafe")


class SafeTerminalTests(unittest.TestCase):
    def test_only_exact_allowlisted_commands_are_accepted(self):
        from xfa_agent.safe_terminal import run_command
        result = run_command("python --version")
        self.assertEqual(result["exit_code"], 0)
        for command in (" /stop", "/stop", "/kill", "rm -rf .", "python -c print(1)", "git status --short; whoami"):
            with self.subTest(command=command), self.assertRaises(ValueError):
                run_command(command)



if __name__ == "__main__":
    unittest.main()
