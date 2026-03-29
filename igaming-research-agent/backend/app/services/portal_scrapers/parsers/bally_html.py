from __future__ import annotations

import datetime
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class BallyHtmlParser(PortalListingParser):
    """Parser for Bally's investor/news pages (Q4-hosted)."""

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return "ballys.com/news/default.aspx" in token_url or "bally" in token_name

    def parse_listing(
        self,
        listing_html: str,
        source_url: str,
        company_name: str,
        cutoff: datetime.datetime | None = None,
        now_utc: datetime.datetime | None = None,
    ) -> ListingParseResult:
        del cutoff, now_utc  # Bally listing is often dynamic; date filtering happens downstream when available.

        result = ListingParseResult()
        html = listing_html or ""
        lower_html = html.lower()

        if "auth.platform.q4inc.com/auth" in lower_html or "error=login_required" in lower_html:
            result.empty_reason = "q4_auth_required"
            return result

        soup = BeautifulSoup(html, "html.parser")
        links = soup.select("a[href*='/news-releases/news-release-details/'], a[href*='/news/news-details/']")
        if not links:
            if "evergreen evergreen-news" in lower_html or "evergreen.q4api" in lower_html:
                result.empty_reason = "q4_dynamic_listing_no_static_links"
                return result
            result.empty_reason = "no_bally_release_links"
            return result

        seen: set[str] = set()
        for link in links:
            href = str(link.get("href") or "").strip()
            absolute_url = urljoin(source_url, href)
            if absolute_url in seen:
                continue
            title = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
            if not title:
                continue
            seen.add(absolute_url)
            result.candidate_urls.append(absolute_url)
            result.candidate_titles[absolute_url] = title

        if not result.candidate_urls:
            result.empty_reason = "no_bally_release_links"

        return result

    def is_likely_descending_chronological(self) -> bool:
        return True
