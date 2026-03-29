from __future__ import annotations

import datetime
import re

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class KalshiHtmlParser(PortalListingParser):
    """Dedicated parser for https://news.kalshi.com listing pages."""

    _PAIR_PATTERN = re.compile(
        r'"web_title"\s*:\s*"(?P<title>(?:\\.|[^"\\])*)".{0,1200}?"slug"\s*:\s*"(?P<slug>[a-z0-9-]+)"',
        flags=re.IGNORECASE | re.DOTALL,
    )

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return "news.kalshi.com" in token_url or "kalshi" in token_name

    def parse_listing(
        self,
        listing_html: str,
        source_url: str,
        company_name: str,
        cutoff: datetime.datetime | None = None,
        now_utc: datetime.datetime | None = None,
    ) -> ListingParseResult:
        result = ListingParseResult()

        seen: set[str] = set()
        for match in self._PAIR_PATTERN.finditer(listing_html or ""):
            slug = (match.group("slug") or "").strip()
            title = (match.group("title") or "").strip()
            if not slug:
                continue

            article_url = f"https://news.kalshi.com/p/{slug}"
            if article_url in seen:
                continue
            seen.add(article_url)
            result.candidate_urls.append(article_url)
            if title:
                # Keep escaped title as hint; article title is still extracted from article page later.
                result.candidate_titles[article_url] = title

        if not result.candidate_urls:
            result.empty_reason = "no_structured_slug_found"

        return result

    def extract_article_published_date(self, article_html: str) -> datetime.datetime | None:
        match = re.search(r'"datePublished"\s*:\s*"([^"\\]+)"', article_html or "", flags=re.IGNORECASE)
        if not match:
            return None
        raw = (match.group(1) or "").strip()
        if not raw:
            return None
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
