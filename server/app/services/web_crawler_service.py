"""Simple web crawler for knowledge ingestion."""

from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urldefrag


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._in_title = False
        self._texts: list[str] = []
        self._links: list[str] = []
        self.title = ""

    @property
    def links(self) -> list[str]:
        return self._links

    @property
    def text(self) -> str:
        lines = [" ".join(x.split()) for x in self._texts]
        lines = [x for x in lines if x]
        return "\n".join(lines)

    def handle_starttag(self, tag: str, attrs) -> None:
        t = tag.lower()
        if t in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if t == "title":
            self._in_title = True
        if t == "a":
            href = dict(attrs).get("href")
            if href:
                self._links.append(href.strip())

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in {"script", "style", "noscript"} and self._skip_depth > 0:
            self._skip_depth -= 1
        if t == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        text = data.strip()
        if not text:
            return
        if self._in_title and not self.title:
            self.title = " ".join(text.split())
        self._texts.append(text)


def _normalize_url(base: str, target: str) -> str | None:
    url = urljoin(base, target)
    url, _ = urldefrag(url)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return None
    return url


def extract_page(html: str, page_url: str) -> tuple[str, str, list[str]]:
    """Return (title, text, links) from HTML."""
    parser = _PageParser()
    parser.feed(html)
    parser.close()
    links: list[str] = []
    for href in parser.links:
        url = _normalize_url(page_url, href)
        if url:
            links.append(url)
    # preserve discovery order while deduplicating
    unique_links = list(dict.fromkeys(links))
    return parser.title, parser.text, unique_links
