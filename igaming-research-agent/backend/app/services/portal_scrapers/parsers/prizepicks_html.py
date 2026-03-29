from __future__ import annotations

import datetime
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class PrizePicksHtmlParser(PortalListingParser):
    """Parser for PrizePicks newsroom/press-news listings."""

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return "prizepicks.com/newsroom" in token_url or "prizepicks" in token_name

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
        links = soup.select("a[href*='/press-news/'][href]")

        if not links:
            result.empty_reason = "no_prizepicks_release_links"
            return result

        seen: set[str] = set()
        for index, link in enumerate(links):
            href = str(link.get("href") or "").strip()
            absolute_url = urljoin(source_url, href)
            if absolute_url in seen:
                continue

            title = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
            if len(title) < 8:
                continue

            context_node = link.find_parent(["article", "li", "div"]) or link.parent
            context_text = re.sub(r"\s+", " ", context_node.get_text(" ", strip=True) if context_node else "").strip()
            published = self._parse_date(context_text)
            if published is None:
                continue
            if cutoff is not None and published < cutoff:
                if index == 0:
                    result.empty_reason = "listing_first_prizepicks_item_outside_time_window"
                    return result
                break
            if now_utc is not None and published > now_utc:
                continue

            seen.add(absolute_url)
            result.candidate_urls.append(absolute_url)
            result.candidate_titles[absolute_url] = title
            result.candidate_published_dates[absolute_url] = published

        if not result.candidate_urls and result.empty_reason is None:
            result.empty_reason = "no_prizepicks_release_links"

        return result

    def is_likely_descending_chronological(self) -> bool:
        return True

    @staticmethod
    def _parse_date(value: str) -> datetime.datetime | None:
        match = re.search(r"\b([A-Za-z]+\s+\d{1,2},\s+\d{4})\b", value or "")
        if not match:
            return None
        try:
            return datetime.datetime.strptime(match.group(1), "%B %d, %Y")
        except ValueError:
            return None
