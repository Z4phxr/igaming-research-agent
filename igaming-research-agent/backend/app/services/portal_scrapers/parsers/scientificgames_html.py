from __future__ import annotations

import datetime
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class ScientificGamesHtmlParser(PortalListingParser):
    """Parser for Scientific Games news listing pages."""

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return "scientificgames.com/news" in token_url or "scientific games" in token_name

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
        links = soup.select("a[href*='/news/news-articles/'][href], a[href*='/news/media-releases/'][href]")

        if not links:
            result.empty_reason = "no_scientificgames_release_links"
            return result

        seen: set[str] = set()
        for index, link in enumerate(links):
            href = str(link.get("href") or "").strip()
            absolute_url = urljoin(source_url, href)
            path = (urlparse(absolute_url).path or "").lower()

            if absolute_url in seen:
                continue
            if "/news/news-articles/" not in path and "/news/media-releases/" not in path:
                continue

            raw_text = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
            title = self._extract_title(raw_text)
            if len(title) < 8:
                continue

            published = self._parse_prefix_date(raw_text)
            if published is not None and cutoff is not None and published < cutoff:
                if index == 0:
                    result.empty_reason = "listing_first_scientificgames_item_outside_time_window"
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
            result.empty_reason = "no_scientificgames_release_links"

        return result

    def is_likely_descending_chronological(self) -> bool:
        return True

    @staticmethod
    def _parse_prefix_date(value: str) -> datetime.datetime | None:
        match = re.match(r"\s*([A-Za-z]{3}\s+\d{1,2},\s+\d{4})\b", value or "")
        if not match:
            return None
        try:
            return datetime.datetime.strptime(match.group(1), "%b %d, %Y")
        except ValueError:
            return None

    @staticmethod
    def _extract_title(value: str) -> str:
        cleaned = re.sub(r"\s+", " ", value or "").strip()
        return re.sub(r"^[A-Za-z]{3}\s+\d{1,2},\s+\d{4}\s+", "", cleaned).strip()
