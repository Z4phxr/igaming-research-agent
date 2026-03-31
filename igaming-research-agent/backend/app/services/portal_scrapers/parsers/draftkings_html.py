from __future__ import annotations

import datetime
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class DraftKingsHtmlParser(PortalListingParser):
    """Parser for DraftKings newsroom listing."""

    _MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://www\.draftkings\.com/[^)\s]+)\)")
    _MARKDOWN_CARD_LINK_RE = re.compile(r"\[#{6}\s+([^\]]+)\]\((https?://www\.draftkings\.com/[^)\s]+)\)")
    _BLOCKED_PATH_FRAGMENTS = (
        "/news-about",
        "/draftkings-about",
        "/who-we-are",
        "/affiliates",
        "/careers",
        "/responsible-gaming",
        "/sportsbook",
        "/casino",
        "/fantasy",
        "/rewards",
        "/about",
    )

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return "draftkings.com/news-about" in token_url or "draftkings" in token_name

    def parse_listing(
        self,
        listing_html: str,
        source_url: str,
        company_name: str,
        cutoff: datetime.datetime | None = None,
        now_utc: datetime.datetime | None = None,
    ) -> ListingParseResult:
        del cutoff, now_utc, company_name

        result = ListingParseResult()
        html = listing_html or ""
        soup = BeautifulSoup(html, "html.parser")

        self._append_html_anchor_candidates(result=result, soup=soup, source_url=source_url)
        if not result.candidate_urls:
            self._append_markdown_candidates(result=result, listing_html=html, source_url=source_url)

        if not result.candidate_urls:
            result.empty_reason = "no_draftkings_release_links"

        return result

    def is_likely_descending_chronological(self) -> bool:
        return True

    def _append_html_anchor_candidates(self, result: ListingParseResult, soup: BeautifulSoup, source_url: str) -> None:
        seen: set[str] = set()
        for anchor in soup.select("a[href]"):
            href = str(anchor.get("href") or "").strip()
            if not href:
                continue
            absolute_url = urljoin(source_url, href)
            if not self._is_article_like_url(absolute_url):
                continue
            if absolute_url in seen:
                continue

            title_node = anchor.select_one("h6")
            if title_node is not None:
                title = re.sub(r"\s+", " ", title_node.get_text(" ", strip=True)).strip()
            else:
                title = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True)).strip()

            if len(title) < 8:
                continue

            seen.add(absolute_url)
            result.candidate_urls.append(absolute_url)
            result.candidate_titles[absolute_url] = title

    def _append_markdown_candidates(self, result: ListingParseResult, listing_html: str, source_url: str) -> None:
        seen = set(result.candidate_urls)
        matches = list(self._MARKDOWN_CARD_LINK_RE.finditer(listing_html or ""))
        if not matches:
            matches = list(self._MARKDOWN_LINK_RE.finditer(listing_html or ""))

        for match in matches:
            title = re.sub(r"\s+", " ", match.group(1)).strip()
            absolute_url = urljoin(source_url, match.group(2).strip())
            if len(title) < 8:
                continue
            if not self._is_article_like_url(absolute_url):
                continue
            if absolute_url in seen:
                continue
            seen.add(absolute_url)
            result.candidate_urls.append(absolute_url)
            result.candidate_titles[absolute_url] = title

    def _is_article_like_url(self, url: str) -> bool:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        if "draftkings.com" not in host:
            return False

        path = (parsed.path or "").strip().lower()
        if not path or path == "/":
            return False
        if any(fragment in path for fragment in self._BLOCKED_PATH_FRAGMENTS):
            return False
        if path.count("/") > 1:
            return False
        if len(path.strip("/")) < 8:
            return False
        if not re.fullmatch(r"/[a-z0-9-]+/?", path):
            return False
        return True