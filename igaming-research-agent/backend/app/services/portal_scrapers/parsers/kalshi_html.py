from __future__ import annotations

import datetime
import json
import re

from bs4 import BeautifulSoup

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
        html = listing_html or ""
        soup = BeautifulSoup(html, "html.parser")

        seen: set[str] = set()
        for link in soup.select("a[href]"):
            href = ((link.get("href") or "")).strip()
            slug = self._extract_slug_from_href(href)
            if not slug:
                continue

            article_url = f"https://news.kalshi.com/p/{slug}"
            if article_url in seen:
                continue
            seen.add(article_url)
            result.candidate_urls.append(article_url)

            title = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
            if title:
                result.candidate_titles[article_url] = title

        # Also parse embedded JSON blobs that include slug + title metadata.
        for script in soup.find_all("script"):
            content = script.string if script.string is not None else script.get_text()
            if not content:
                continue
            for slug, title in self._extract_slug_title_pairs(content):
                article_url = f"https://news.kalshi.com/p/{slug}"
                if article_url in seen:
                    continue
                seen.add(article_url)
                result.candidate_urls.append(article_url)
                if title:
                    result.candidate_titles[article_url] = title

        # Fallback: regex scan over full HTML for non-standard payload formatting.
        for slug, title in self._extract_slug_title_pairs(html):
            article_url = f"https://news.kalshi.com/p/{slug}"
            if article_url in seen:
                continue
            seen.add(article_url)
            result.candidate_urls.append(article_url)
            if title:
                result.candidate_titles[article_url] = title

        if not result.candidate_urls:
            result.empty_reason = "no_structured_slug_found"

        return result

    def _extract_slug_title_pairs(self, content: str) -> list[tuple[str, str]]:
        pairs: list[tuple[str, str]] = []

        for match in self._PAIR_PATTERN.finditer(content or ""):
            slug = (match.group("slug") or "").strip()
            title = (match.group("title") or "").strip()
            if not slug:
                continue
            pairs.append((slug, title))

        # JSON-LD and script payload variant where title key is "title" instead of "web_title".
        for match in re.finditer(r'\{[^{}]*"slug"\s*:\s*"([a-z0-9-]+)"[^{}]*\}', content or "", flags=re.IGNORECASE):
            raw_obj = match.group(0)
            try:
                data = json.loads(raw_obj)
            except Exception:
                continue
            slug = str(data.get("slug", "")).strip()
            if not slug:
                continue
            title = str(data.get("web_title") or data.get("title") or "").strip()
            pairs.append((slug, title))

        return pairs

    @staticmethod
    def _extract_slug_from_href(href: str) -> str | None:
        value = (href or "").strip()
        if not value:
            return None
        match = re.search(r"/(?:p|post)/([a-z0-9-]+)(?:$|[/?#])", value, flags=re.IGNORECASE)
        if match:
            return (match.group(1) or "").strip().lower()
        return None

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
