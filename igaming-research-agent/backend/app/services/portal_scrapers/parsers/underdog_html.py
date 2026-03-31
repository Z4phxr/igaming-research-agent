from __future__ import annotations

import datetime
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class UnderdogHtmlParser(PortalListingParser):
    """Dedicated parser for Underdog newsroom."""

    _PRESS_RELEASE_TAG = re.compile(r"\bPress\s+Releases\b", flags=re.IGNORECASE)

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return "underdogfantasy.com/news" in token_url or "underdog" in token_name

    def parse_listing(
        self,
        listing_html: str,
        source_url: str,
        company_name: str,
        cutoff: datetime.datetime | None = None,
        now_utc: datetime.datetime | None = None,
    ) -> ListingParseResult:
        result = ListingParseResult()
        soup = BeautifulSoup(listing_html or "", "html.parser")
        links = soup.select("a[href*='/news/']")

        if not links:
            result.empty_reason = "no_underdog_news_links"
            return result

        seen: set[str] = set()
        for index, link in enumerate(links):
            href = str(link.get("href") or "").strip()
            absolute_url = urljoin(source_url, href)
            if "underdogfantasy.com/news/" not in absolute_url.lower():
                continue
            if absolute_url.rstrip("/").lower().endswith("/news"):
                continue
            if absolute_url in seen:
                continue

            row_text = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
            if not row_text:
                continue
            if not self._PRESS_RELEASE_TAG.search(row_text):
                continue

            published = self._extract_date(row_text)
            title = self._extract_title(row_text)
            if not title:
                title = row_text

            if published is not None and cutoff is not None and published < cutoff:
                if index == 0:
                    result.empty_reason = "listing_first_underdog_item_outside_time_window"
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
            result.empty_reason = "no_underdog_press_release_links"

        return result

    def is_likely_descending_chronological(self) -> bool:
        return True

    @staticmethod
    def _extract_date(value: str) -> datetime.datetime | None:
        text = value or ""
        for pattern, fmt in [
            (r"\b([A-Z][a-z]+\s+\d{1,2},\s+\d{4})\b", "%B %d, %Y"),
            (r"\b([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})\b", "%b %d, %Y"),
        ]:
            match = re.search(pattern, text)
            if not match:
                continue
            try:
                return datetime.datetime.strptime(match.group(1), fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _extract_title(value: str) -> str:
        text = re.sub(r"\s+", " ", value or "").strip()
        text = re.sub(r"^[A-Z][a-z]+\s+\d{1,2},\s+\d{4}\s+\d+\s*min\s+", "", text)
        text = re.sub(r"^[A-Z][a-z]+\s+\d{1,2},\s+\d{4}\s+", "", text)
        text = re.sub(r"\bPress\s+Releases\b\s*", "", text, flags=re.IGNORECASE)
        return text.strip()
