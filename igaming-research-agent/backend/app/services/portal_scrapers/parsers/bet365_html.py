from __future__ import annotations

import datetime
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class Bet365HtmlParser(PortalListingParser):
    """Dedicated parser for bet365 news section pages."""

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return "news.bet365.com" in token_url or "bet365" in token_name

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
        links = soup.select("a[href*='/article/'][href]")

        if not links:
            result.empty_reason = "no_bet365_article_links"
            return result

        seen: set[str] = set()
        for index, link in enumerate(links):
            href = str(link.get("href") or "").strip()
            absolute_url = urljoin(source_url, href)
            if absolute_url in seen:
                continue

            title = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
            if not title:
                continue

            published = self._parse_date_from_url(absolute_url)
            if published is not None and cutoff is not None and published < cutoff:
                if index == 0:
                    result.empty_reason = "listing_first_bet365_item_outside_time_window"
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
            result.empty_reason = "no_bet365_in_window_links"

        return result

    def is_likely_descending_chronological(self) -> bool:
        return True

    @staticmethod
    def _parse_date_from_url(url: str) -> datetime.datetime | None:
        # bet365 article URLs end with long numeric IDs; first 8 digits are YYYYMMDD.
        match = re.search(r"/(\d{8})\d{6,}$", url or "")
        if not match:
            return None
        try:
            return datetime.datetime.strptime(match.group(1), "%Y%m%d")
        except ValueError:
            return None
