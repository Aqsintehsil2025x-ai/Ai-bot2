import unittest

import remote_dev_agent as agent


class RemoteDevSecurityTests(unittest.TestCase):
    def test_rejects_parent_traversal(self):
        with self.assertRaises(ValueError):
            agent._safe_path("../outside.py")

    def test_rejects_hidden_paths(self):
        with self.assertRaises(ValueError):
            agent._safe_path(".env")
        with self.assertRaises(ValueError):
            agent._safe_path(".git/config")

    def test_rejects_unsupported_extensions(self):
        with self.assertRaises(ValueError):
            agent._safe_path("run.sh", writing=True)

    def test_allows_project_source_file(self):
        path = agent._safe_path("main.py")
        self.assertTrue(path.is_file())

    def test_mcp_initialize(self):
        response = agent._rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        self.assertEqual(response["result"]["serverInfo"]["name"], "xfa-replit-remote-dev")

    def test_mcp_lists_only_allowlisted_tools(self):
        response = agent._rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = {item["name"] for item in response["result"]["tools"]}
        self.assertEqual(names, {"workspace_status", "read_file", "write_file", "run_check"})
        self.assertNotIn("shell", names)


if __name__ == "__main__":
    unittest.main()
