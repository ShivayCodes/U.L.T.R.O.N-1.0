"""Small, explicit DuckDuckGo HTML search adapter (standard library only)."""
from __future__ import annotations

from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen


class _ResultsParser(HTMLParser):
    """Extract only visible result title/snippet text and result links."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[dict[str, str]] = []
        self._capture: str | None = None
        self._title_tag: str | None = None
        self._snippet_tag: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "a" and "result__a" in classes:
            raw_url = attributes.get("href") or ""
            parsed = urlparse(raw_url)
            if parsed.hostname and parsed.hostname.endswith("duckduckgo.com"):
                target = parse_qs(parsed.query).get("uddg", [""])[0]
                raw_url = target or raw_url
            if urlparse(raw_url).scheme in {"http", "https"}:
                self.results.append({"title": "", "url": raw_url, "snippet": ""})
                self._capture = "title"
                self._title_tag = tag
        elif tag in {"a", "div", "td"} and "result__snippet" in classes and self.results:
            self._capture = "snippet"
            self._snippet_tag = tag

    def handle_endtag(self, tag: str) -> None:
        if self._capture == "title" and tag == self._title_tag:
            self._capture = None
            self._title_tag = None
        elif self._capture == "snippet" and tag == self._snippet_tag:
            self._capture = None
            self._snippet_tag = None

    def handle_data(self, data: str) -> None:
        if not self._capture or not self.results:
            return
        key = self._capture
        self.results[-1][key] += data


def parse_search_results(document: str, limit: int = 5) -> list[dict[str, str]]:
    """Parse bounded text results from a DuckDuckGo HTML response."""
    parser = _ResultsParser()
    parser.feed(document)
    results = []
    for result in parser.results:
        title = " ".join(result["title"].split())
        snippet = " ".join(result["snippet"].split())
        if title and result["url"]:
            results.append({"title": title[:300], "url": result["url"][:2_000], "snippet": snippet[:1_000]})
        if len(results) >= max(0, limit):
            break
    return results


def search_web(query: str, *, limit: int = 5, timeout: int = 8) -> list[dict[str, str]]:
    """Search DuckDuckGo when explicitly requested; does not open result pages."""
    cleaned = query.strip()
    if not cleaned:
        raise ValueError("Search query cannot be empty.")
    if len(cleaned) > 300:
        raise ValueError("Search query must be 300 characters or fewer.")
    url = "https://html.duckduckgo.com/html/?" + urlencode({"q": cleaned})
    request = Request(
        url,
        headers={"User-Agent": "ULTRON-local-assistant/1.0 (explicit user search)", "Accept": "text/html"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            document = response.read(1_000_001)
    except HTTPError as exc:
        raise RuntimeError(f"Search service returned HTTP {exc.code}.") from exc
    except URLError as exc:
        raise RuntimeError(f"Search service is unreachable: {exc.reason}") from exc
    if len(document) > 1_000_000:
        raise RuntimeError("Search response exceeded the 1 MB safety limit.")
    return parse_search_results(document.decode("utf-8", errors="replace"), limit=limit)
