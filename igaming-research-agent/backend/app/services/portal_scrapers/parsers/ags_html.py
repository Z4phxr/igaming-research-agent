from __future__ import annotations

import datetime
import re
from urllib.parse import urljoin
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class AgsHtmlParser(PortalListingParser):
    """Parser for AGS newsroom pages."""

    _KEYWORDS = ("press", "release", "news", "media")

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return "playags.com" in token_url or " ags" in f" {token_name}"

    def parse_listing(
        self,
        listing_html: str,
        source_url: str,
        company_name: str,
        cutoff: datetime.datetime | None = None,
        now_utc: datetime.datetime | None = None,
    ) -> ListingParseResult:
        del cutoff, now_utc

        result = ListingParseResult()
        html = listing_html or ""
        lower_html = html.lower()

        if "ssl" in lower_html and "certificate" in lower_html:
            result.empty_reason = "tls_certificate_error"
            return result

        soup = BeautifulSoup(html, "html.parser")
        links = soup.select("a[href]")
        if not links:
            result.empty_reason = "no_ags_links_found"
            return result

        seen: set[str] = set()
        for link in links:
            href = str(link.get("href") or "").strip()
            if not href:
                continue
            absolute_url = urljoin(source_url, href)
            parsed = urlparse(absolute_url)
            searchable = f"{parsed.path}?{parsed.query}".lower()
            if absolute_url in seen:
                continue
            if not any(word in searchable for word in self._KEYWORDS):
                continue
            if absolute_url.rstrip("/").lower() in {
                "https://newsroom.playags.com",
                "https://newsroom.playags.com/newsroom",
            }:
                continue

            title = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
            if not title:
                continue

            seen.add(absolute_url)
            result.candidate_urls.append(absolute_url)
            result.candidate_titles[absolute_url] = title

        if not result.candidate_urls:
            result.empty_reason = "no_ags_release_links"

        return result

    def is_likely_descending_chronological(self) -> bool:
        return True
