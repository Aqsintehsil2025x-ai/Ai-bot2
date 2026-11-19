import unittest

from cogs.community_suite import _normalise


class CommunitySuiteTests(unittest.TestCase):
    def test_normalise_collapses_whitespace_and_casefolds(self):
        self.assertEqual(_normalise("  SERVER   RULES  "), "server rules")

    def test_normalise_handles_empty_input(self):
        self.assertEqual(_normalise("   "), "")


if __name__ == "__main__":
    unittest.main()
