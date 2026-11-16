"""Small, keyless public-web search adapter for XFA.

Search results are treated as untrusted reference material. XFA does not open pages
or perform actions based on instructions found in search snippets.
"""
from __future__ import annotations

import html
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urlparse, parse_qs


class _SearchParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results = []
        self._current = None
        self._capture = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "a" and "result__a" in classes:
            href = html.unescape(attributes.get("href", ""))
            self._current = {"title": "", "url": _unwrap_url(href), "snippet": ""}
            self._capture = "title"
        elif tag in {"a", "td", "div"} and "result__snippet" in classes and self._current:
            self._capture = "snippet"

    def handle_data(self, data):
        if self._current and self._capture in {"title", "snippet"}:
            self._current[self._capture] += data

    def handle_endtag(self, tag):
        if tag == "a" and self._capture == "title" and self._current:
            self._capture = None
        elif tag in {"a", "td", "div"} and self._capture == "snippet" and self._current:
            self._capture = None
            self.results.append(self._current)
            self._current = None


def _unwrap_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.hostname and parsed.hostname.endswith("duckduckgo.com"):
        target = parse_qs(parsed.query).get("uddg", [""])[0]
        return urllib.parse.unquote(target)
    return value


def search_public_web(query: str, limit: int = 5) -> list[dict]:
    query = str(query or "").strip()
    if not query or len(query) > 300:
        raise ValueError("Axtarış sorğusu 1-300 simvol olmalıdır.")
    limit = max(1, min(int(limit), 5))
    url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; XFA/1.0; +https://example.invalid)",
            "Accept": "text/html",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read(2 * 1024 * 1024)
    except Exception as exc:
        raise RuntimeError("İctimai internet axtarışı hazırda əlçatan deyil.") from exc
    parser = _SearchParser()
    parser.feed(raw.decode("utf-8", errors="replace"))
    output = []
    seen = set()
    for item in parser.results:
        target = item["url"].strip()
        parsed = urlparse(target)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or target in seen:
            continue
        title = " ".join(item["title"].split())[:240]
        snippet = " ".join(item["snippet"].split())[:600]
        if not title:
            continue
        seen.add(target)
        output.append({"title": title, "url": target, "snippet": snippet})
        if len(output) >= limit:
            break
    return output
