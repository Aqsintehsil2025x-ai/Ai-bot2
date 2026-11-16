import unittest

from xfa_agent.web_search import _SearchParser, _unwrap_url, search_public_web


class XFAWebSearchTests(unittest.TestCase):
    def test_parser_extracts_result_title_and_snippet(self):
        parser = _SearchParser()
        parser.feed(
            '<a class="result__a" href="https://example.com/page">Example title</a>'
            '<a class="result__snippet">A useful public snippet.</a>'
        )
        self.assertEqual(len(parser.results), 1)
        self.assertEqual(parser.results[0]["title"], "Example title")
        self.assertEqual(parser.results[0]["snippet"], "A useful public snippet.")
        self.assertEqual(parser.results[0]["url"], "https://example.com/page")

    def test_duckduckgo_redirect_is_unwrapped(self):
        target = "https://example.com/a?x=1"
        redirect = "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fa%3Fx%3D1"
        self.assertEqual(_unwrap_url(redirect), target)

    def test_search_query_is_bounded_before_network_access(self):
        with self.assertRaises(ValueError):
            search_public_web("x" * 301)


if __name__ == "__main__":
    unittest.main()
