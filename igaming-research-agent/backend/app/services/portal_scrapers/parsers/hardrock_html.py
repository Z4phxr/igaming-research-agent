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
        cards = soup.select(".cfcards.news-cf")

        if not cards:
            cards = soup.select("a[href^='/blog/']")

        if not cards:
            result.empty_reason = "no_hardrock_news_cards"
            return result

        seen: set[str] = set()

        if cards and hasattr(cards[0], "select") and cards[0].name != "a":
            for index, card in enumerate(cards):
                link = card.select_one("a[href^='/blog/']")
                if link is None:
                    continue
                href = str(link.get("href") or "").strip()
                absolute_url = urljoin(source_url, href)
                if self._is_excluded(absolute_url):
                    continue
                if absolute_url in seen:
                    continue

                title = ""
                title_node = card.select_one("h2, h3, h4")
                if title_node is not None:
                    title = re.sub(r"\s+", " ", title_node.get_text(" ", strip=True)).strip()

                published = self._extract_listing_date(card)
                if published is not None and cutoff is not None and published < cutoff:
                    if index == 0:
                        result.empty_reason = "listing_first_hardrock_item_outside_time_window"
                        return result
                    break

                if published is not None and now_utc is not None and published > now_utc:
                    continue

                seen.add(absolute_url)
                result.candidate_urls.append(absolute_url)
                if title:
                    result.candidate_titles[absolute_url] = title
                if published is not None:
                    result.candidate_published_dates[absolute_url] = published
        else:
            for link in cards:
                href = str(link.get("href") or "").strip()
                absolute_url = urljoin(source_url, href)
                if self._is_excluded(absolute_url):
                    continue
                if absolute_url in seen:
                    continue

                seen.add(absolute_url)
                result.candidate_urls.append(absolute_url)
                title = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
                if title and title.lower() != "read more":
                    result.candidate_titles[absolute_url] = title

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
    def _extract_listing_date(card: BeautifulSoup) -> datetime.datetime | None:
        text = re.sub(r"\s+", " ", card.get_text(" ", strip=True)).strip()
        match = re.search(r"\b([A-Z][a-z]+\s+\d{1,2},\s+\d{4})\b", text)
        if not match:
            return None
        raw = match.group(1)
        try:
            return datetime.datetime.strptime(raw, "%B %d, %Y")
        except ValueError:
            return None
