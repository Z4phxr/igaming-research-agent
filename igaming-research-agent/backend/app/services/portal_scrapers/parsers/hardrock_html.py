from __future__ import annotations

import datetime
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class HardRockHtmlParser(PortalListingParser):
    """Dedicated parser for Hard Rock newsroom/blog pages."""

    _EXCLUDED_PATH_MARKERS = (
        "/blog/results.",
        "/blog/results/category",
        "/blog/results.page",
    )

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return "hardrock.com/blog" in token_url or "hard rock" in token_name

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
        
        # Look for article cards in the AEM Grid structure
        cards = soup.select("div.cfcards.news-cf.cmp-button--primary")
        
        if not cards:
            result.empty_reason = "no_hardrock_news_cards"
            return result

        seen: set[str] = set()

        for index, card in enumerate(cards):
            # Extract title link from .cmp-teaser__title
            title_link = card.select_one("a.cmp-teaser__title")
            if title_link is None:
                continue
                
            href = str(title_link.get("href") or "").strip()
            if not href:
                continue
                
            absolute_url = urljoin(source_url, href)
            if self._is_excluded(absolute_url):
                continue
            if absolute_url in seen:
                continue

            title = re.sub(r"\s+", " ", title_link.get_text(" ", strip=True)).strip()
            if not title:
                continue

            # Extract date from .cmp-teaser__date
            date_elem = card.select_one("h3.cmp-teaser__date")
            published = self._parse_date_from_element(date_elem) if date_elem else None
            
            if published is not None and cutoff is not None and published < cutoff:
                if index == 0:
                    result.empty_reason = "listing_first_hardrock_item_outside_time_window"
                    return result
                break

            if published is not None and now_utc is not None and published > now_utc:
                continue

            seen.add(absolute_url)
            result.candidate_urls.append(absolute_url)
            result.candidate_titles[absolute_url] = title
            if published is not None:
                result.candidate_published_dates[absolute_url] = published

        if not result.candidate_urls:
            result.empty_reason = "no_hardrock_article_links"

        return result

    def is_likely_descending_chronological(self) -> bool:
        return True

    def _is_excluded(self, absolute_url: str) -> bool:
        normalized = absolute_url.rstrip("/").lower()
        if normalized.endswith("/blog"):
            return True
        return any(marker in normalized for marker in self._EXCLUDED_PATH_MARKERS)

    @staticmethod
    def _parse_date_from_element(date_elem) -> datetime.datetime | None:
        """Extract date from h3.cmp-teaser__date element (format: 'Month DD, YYYY')."""
        text = re.sub(r"\s+", " ", date_elem.get_text(" ", strip=True)).strip() if date_elem else None
        if not text:
            return None
        match = re.search(r"\b([A-Z][a-z]+\s+\d{1,2},\s+\d{4})\b", text)
        if not match:
            return None
        raw = match.group(1)
        try:
            return datetime.datetime.strptime(raw, "%B %d, %Y")
        except ValueError:
            return None
