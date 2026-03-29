from __future__ import annotations

import datetime
import re
from urllib.parse import urljoin

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class EvolutionHtmlParser(PortalListingParser):
    """Dedicated parser for Evolution news cards on evolution.com/news."""

    _CARD_PATTERN = re.compile(
        r'<a[^>]+href="(?P<href>[^"]+)"[^>]*class="[^"]*news-card[^"]*"[^>]*>'
        r'.*?<span[^>]*class="[^"]*news-card-date[^"]*"[^>]*>(?P<date>[^<]+)</span>'
        r'.*?<p[^>]*class="[^"]*h4[^"]*"[^>]*>(?P<title>.*?)</p>',
        flags=re.IGNORECASE | re.DOTALL,
    )

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
        html = listing_html or ""
        cards = list(self._CARD_PATTERN.finditer(html))

        if not cards:
            result.empty_reason = "no_news_cards_found"
            return result

        seen: set[str] = set()
        for index, match in enumerate(cards):
            href = (match.group("href") or "").strip()
            title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", match.group("title") or "")).strip()
            raw_date = re.sub(r"\s+", "", match.group("date") or "")
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
