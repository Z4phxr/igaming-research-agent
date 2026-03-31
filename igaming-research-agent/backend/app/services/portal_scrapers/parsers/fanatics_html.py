from __future__ import annotations

import datetime
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class FanaticsHtmlParser(PortalListingParser):
    """Dedicated parser for Fanatics press releases listing."""

    _DATE_PATTERN = re.compile(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b")

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return "fanaticsinc.com/press-releases" in token_url or "fanatics" in token_name

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
        cards = soup.select("article.blog-basic-grid--container.entry.blog-item")

        if not cards:
            cards = soup.select("article.entry.blog-item")

        if not cards:
            result.empty_reason = "no_fanatics_release_cards"
            return result

        seen: set[str] = set()
        for index, card in enumerate(cards):
            link = card.select_one("a[href*='/press-releases/']:not([href*='/category/'])")
            if link is None:
                continue

            href = str(link.get("href") or "").strip()
            absolute_url = urljoin(source_url, href)
            normalized = absolute_url.rstrip("/").lower()
            if normalized.endswith("/press-releases"):
                continue
            if absolute_url in seen:
                continue

            title = ""
            title_node = card.select_one("h2, h3, h4")
            if title_node is not None:
                title = re.sub(r"\s+", " ", title_node.get_text(" ", strip=True)).strip()
            if not title:
                title = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()

            published = self._extract_listing_date(card)
            if published is not None and cutoff is not None and published < cutoff:
                if index == 0:
                    result.empty_reason = "listing_first_fanatics_item_outside_time_window"
                    return result
                break

            if published is not None and now_utc is not None and published > now_utc:
                continue

            seen.add(absolute_url)
            result.candidate_urls.append(absolute_url)
            if title and title.lower() != "read more":
                result.candidate_titles[absolute_url] = title
            if published is not None:
                result.candidate_published_dates[absolute_url] = published

        if not result.candidate_urls and result.empty_reason is None:
            result.empty_reason = "no_fanatics_release_links"

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
            parsed = self._parse_datetime(match.group(1))
            if parsed is not None:
                return parsed
        return None

    def is_likely_descending_chronological(self) -> bool:
        return True

    def _extract_listing_date(self, card: BeautifulSoup) -> datetime.datetime | None:
        date_nodes = card.select("time, .entry-date, .blog-basic-grid--date")
        for node in date_nodes:
            value = re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()
            parsed = self._parse_date_text(value)
            if parsed is not None:
                return parsed

        card_text = re.sub(r"\s+", " ", card.get_text(" ", strip=True)).strip()
        match = self._DATE_PATTERN.search(card_text)
        if match:
            return self._parse_date_text(match.group(1))
        return None

    @staticmethod
    def _parse_date_text(value: str) -> datetime.datetime | None:
        raw = (value or "").strip()
        if not raw:
            return None
        for fmt in ("%m/%d/%y", "%m/%d/%Y", "%b %d, %Y", "%B %d, %Y"):
            try:
                return datetime.datetime.strptime(raw, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _parse_datetime(value: str) -> datetime.datetime | None:
        raw = (value or "").strip()
        if not raw:
            return None

        candidates = [raw]
        if raw.endswith("Z"):
            candidates.append(raw[:-1] + "+00:00")
        candidates.append(raw.replace("-0700", "-07:00").replace("-0800", "-08:00"))

        for candidate in candidates:
            try:
                parsed = datetime.datetime.fromisoformat(candidate)
                if parsed.tzinfo is not None:
                    return parsed.astimezone(datetime.timezone.utc).replace(tzinfo=None)
                return parsed
            except ValueError:
                continue
        return None
