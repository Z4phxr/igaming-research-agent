from __future__ import annotations

import datetime
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class PennHtmlParser(PortalListingParser):
    """Dedicated parser for PENN Entertainment investor press releases."""

    _DATE_PATTERNS = (
        re.compile(r"\b([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})\b"),
        re.compile(r"\b([A-Z][a-z]+\s+\d{1,2},\s+\d{4})\b"),
    )

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return (
            "investors.pennentertainment.com/press-releases" in token_url
            or "penn entertainment" in token_name
            or "espn bet" in token_name
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
        soup = BeautifulSoup(listing_html or "", "html.parser")

        # Find all article elements from NIR widget structure
        articles = soup.select("article[class*='nir-news']")
        if not articles:
            result.empty_reason = "no_penn_articles_found"
            return result

        seen: set[str] = set()
        for index, article in enumerate(articles):
            # Extract date from dedicated date div
            date_div = article.select_one("div.nir-widget--news--date-time")
            date_text = re.sub(r"\s+", " ", date_div.get_text(" ", strip=True)).strip() if date_div else None
            published = self._parse_date_from_text(date_text) if date_text else None

            # Extract link from headline div
            headline_div = article.select_one("div.nir-widget--news--headline a")
            if not headline_div:
                continue

            href = str(headline_div.get("href") or "").strip()
            if not href:
                continue

            absolute_url = urljoin(source_url, href)
            if absolute_url in seen:
                continue

            title = re.sub(r"\s+", " ", headline_div.get_text(" ", strip=True)).strip()
            if not title:
                continue

            # Apply cutoff filtering
            if published is not None and cutoff is not None and published < cutoff:
                if index == 0:
                    result.empty_reason = "listing_first_penn_item_outside_time_window"
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
            result.empty_reason = "no_penn_in_window_links"

        return result

    def is_likely_descending_chronological(self) -> bool:
        return True

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
