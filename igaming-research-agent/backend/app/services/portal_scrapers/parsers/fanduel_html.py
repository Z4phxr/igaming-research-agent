from __future__ import annotations

import datetime
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class FanDuelHtmlParser(PortalListingParser):
    """Dedicated parser for FanDuel newsroom listing at /about/news."""

    _EXCLUDED_SUFFIXES = ("/about/news/faqs", "/about/news/company-news/all")

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return "fanduel.com/about/news" in token_url or "fanduel" in token_name

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

        cards = soup.select("a.ArticlePreviewLink_article__fkeM_[href*='/about/news/']")
        if not cards:
            cards = soup.select("a[href*='/about/news/']")

        if not cards:
            result.empty_reason = "no_fanduel_news_cards_found"
            return result

        seen: set[str] = set()
        for card in cards:
            href = str(card.get("href") or "").strip()
            if not href:
                continue

            absolute_url = urljoin(source_url, href)
            normalized = absolute_url.rstrip("/").lower()
            if any(normalized.endswith(suffix) for suffix in self._EXCLUDED_SUFFIXES):
                continue

            if absolute_url in seen:
                continue
            seen.add(absolute_url)

            result.candidate_urls.append(absolute_url)

            title_node = card.select_one("h2, h3, h4")
            if title_node is not None:
                title = re.sub(r"\s+", " ", title_node.get_text(" ", strip=True)).strip()
                if title:
                    result.candidate_titles[absolute_url] = title

        if not result.candidate_urls:
            result.empty_reason = "no_fanduel_article_links"

        return result

    def extract_article_published_date(self, article_html: str) -> datetime.datetime | None:
        patterns = [
            r'"datePublished"\s*:\s*"([^"\\]+)"',
            r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, article_html or "", flags=re.IGNORECASE)
            if not match:
                continue
            raw = (match.group(1) or "").strip()
            if not raw:
                continue
            candidates = [raw]
            if raw.endswith("Z"):
                candidates.append(raw[:-1] + "+00:00")
            for candidate in candidates:
                try:
                    value = datetime.datetime.fromisoformat(candidate)
                    if value.tzinfo is not None:
                        return value.astimezone(datetime.timezone.utc).replace(tzinfo=None)
                    return value
                except ValueError:
                    continue
        return None

    def is_likely_descending_chronological(self) -> bool:
        return True
