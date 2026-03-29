from __future__ import annotations

import datetime
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class RsiHtmlParser(PortalListingParser):
    """Parser for Rush Street Interactive investor newsroom pages (Q4-hosted)."""

    _DATE_PATTERNS = (
        re.compile(r"\b([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})\b"),
        re.compile(r"\b([A-Z][a-z]+\s+\d{1,2},\s+\d{4})\b"),
    )

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return (
            "ir.rushstreetinteractive.com/news" in token_url
            or "rush street interactive" in token_name
            or "betrivers" in token_name
        )

    def parse_listing(
        self,
        listing_html: str,
        source_url: str,
        company_name: str,
        cutoff: datetime.datetime | None = None,
        now_utc: datetime.datetime | None = None,
    ) -> ListingParseResult:
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
            result.empty_reason = "no_rsi_release_links"
            return result

        seen: set[str] = set()
        for index, link in enumerate(links):
            href = str(link.get("href") or "").strip()
            if not href:
                continue
            absolute_url = urljoin(source_url, href)
            if absolute_url in seen:
                continue

            title = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
            if not title:
                continue

            published = self._extract_nearby_date(link)
            if published is not None and cutoff is not None and published < cutoff:
                if index == 0:
                    result.empty_reason = "listing_first_rsi_item_outside_time_window"
                    return result
                break

            if published is not None and now_utc is not None and published > now_utc:
                continue

            seen.add(absolute_url)
            result.candidate_urls.append(absolute_url)
            result.candidate_titles[absolute_url] = title
            if published is not None:
                result.candidate_published_dates[absolute_url] = published

        if not result.candidate_urls and result.empty_reason is None:
            result.empty_reason = "no_rsi_in_window_links"

        return result

    def is_likely_descending_chronological(self) -> bool:
        return True

    def _extract_nearby_date(self, link: Tag) -> datetime.datetime | None:
        parent_text = re.sub(r"\s+", " ", link.parent.get_text(" ", strip=True) if link.parent else "").strip()
        for candidate in (parent_text, self._window_text(link)):
            parsed = self._parse_date_from_text(candidate)
            if parsed is not None:
                return parsed
        return None

    @classmethod
    def _parse_date_from_text(cls, text: str) -> datetime.datetime | None:
        value = (text or "").strip()
        if not value:
            return None
        for pattern in cls._DATE_PATTERNS:
            match = pattern.search(value)
            if not match:
                continue
            raw = match.group(1)
            for fmt in ("%b %d, %Y", "%B %d, %Y"):
                try:
                    return datetime.datetime.strptime(raw, fmt)
                except ValueError:
                    continue
        return None

    @staticmethod
    def _window_text(link: Tag) -> str:
        snippets: list[str] = []
        prev = link.previous_sibling
        nxt = link.next_sibling
        if isinstance(prev, str):
            snippets.append(prev)
        if isinstance(nxt, str):
            snippets.append(nxt)
        return re.sub(r"\s+", " ", " ".join(snippets)).strip()
