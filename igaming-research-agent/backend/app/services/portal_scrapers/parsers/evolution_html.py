from __future__ import annotations

import datetime
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class EvolutionHtmlParser(PortalListingParser):
    """Dedicated parser for Evolution news cards on evolution.com/news."""

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return "evolution.com/news" in token_url or "evolution" in token_name

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
        cards = soup.select("a.news-card[href]")

        if not cards:
            result.empty_reason = "no_news_cards_found"
            return result

        seen: set[str] = set()
        for index, card in enumerate(cards):
            href = ((card.get("href") or "")).strip()

            date_node = card.select_one(".news-card-date")
            raw_date = ""
            if date_node is not None:
                raw_date = re.sub(r"\s+", "", date_node.get_text(strip=True))

            title_node = card.select_one("p.h4") or card.select_one("h1, h2, h3, h4, h5")
            title = ""
            if title_node is not None:
                title = re.sub(r"\s+", " ", title_node.get_text(" ", strip=True)).strip()

            published = self._parse_card_date(raw_date)
            absolute_url = urljoin(source_url, href)

            if published is not None and cutoff is not None and published < cutoff:
                if index == 0:
                    result.empty_reason = "listing_first_card_outside_time_window"
                    return result
                # Cards are newest -> oldest, so stale means everything below is stale too.
                break

            if published is not None and now_utc is not None and published > now_utc:
                continue

            if not absolute_url or absolute_url in seen:
                continue
            seen.add(absolute_url)
            result.candidate_urls.append(absolute_url)
            if title:
                result.candidate_titles[absolute_url] = title
            if published is not None:
                result.candidate_published_dates[absolute_url] = published

        if not result.candidate_urls and result.empty_reason is None:
            result.empty_reason = "no_in_window_cards"

        return result

    def is_likely_descending_chronological(self) -> bool:
        return True

    @staticmethod
    def _parse_card_date(raw: str) -> datetime.datetime | None:
        value = (raw or "").strip()
        if not value:
            return None
        try:
            # Evolution listing date format: DD/MM/YY
            return datetime.datetime.strptime(value, "%d/%m/%y")
        except ValueError:
            return None
