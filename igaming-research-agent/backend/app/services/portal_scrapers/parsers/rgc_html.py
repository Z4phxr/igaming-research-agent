from __future__ import annotations

import datetime
import json
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class RgcHtmlParser(PortalListingParser):
    """Parser for Responsible Gambling Council (RGC) newsroom listings."""

    _RGC_CONTENT_RE = re.compile(r"var\s+rgc_content\s*=\s*(\{.*?\})\s*;", re.DOTALL)

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return (
            "responsiblegambling.org/news" in token_url
            or "responsiblegambling.org/about-rgc/rgc-news" in token_url
            or "responsible gambling council" in token_name
        )

    def parse_listing(
        self,
        listing_html: str,
        source_url: str,
        company_name: str,
        cutoff: datetime.datetime | None = None,
        now_utc: datetime.datetime | None = None,
    ) -> ListingParseResult:
        html = listing_html or ""
        result = ListingParseResult()

        json_items = self._extract_rgc_articles_json(html)
        if json_items:
            self._append_json_candidates(
                result=result,
                items=json_items,
                source_url=source_url,
                cutoff=cutoff,
                now_utc=now_utc,
            )
            return result

        # Fallback for simple static HTML snippets in tests/snapshots.
        soup = BeautifulSoup(html, "html.parser")
        links = soup.select("a[href*='/about-rgc/rgc-news/'][href]")
        if not links:
            result.empty_reason = "no_rgc_news_links"
            return result

        seen: set[str] = set()
        for link in links:
            href = str(link.get("href") or "").strip()
            absolute_url = urljoin(source_url, href)
            if absolute_url in seen:
                continue
            if (urlparse(absolute_url).path or "").rstrip("/").endswith("/about-rgc/rgc-news"):
                continue

            title = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
            if len(title) < 8:
                continue

            seen.add(absolute_url)
            result.candidate_urls.append(absolute_url)
            result.candidate_titles[absolute_url] = title

        if not result.candidate_urls:
            result.empty_reason = "no_rgc_news_links"

        return result

    def is_likely_descending_chronological(self) -> bool:
        return True

    @classmethod
    def _extract_rgc_articles_json(cls, html: str) -> list[dict]:
        match = cls._RGC_CONTENT_RE.search(html or "")
        if not match:
            return []
        raw = str(match.group(1) or "").strip()
        if not raw:
            return []
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return []
        articles = payload.get("articles") if isinstance(payload, dict) else None
        if not isinstance(articles, list):
            return []
        return [item for item in articles if isinstance(item, dict)]

    def _append_json_candidates(
        self,
        result: ListingParseResult,
        items: list[dict],
        source_url: str,
        cutoff: datetime.datetime | None,
        now_utc: datetime.datetime | None,
    ) -> None:
        seen: set[str] = set()
        for index, item in enumerate(items):
            href = str(item.get("url") or "").strip()
            if not href:
                continue
            absolute_url = urljoin(source_url, href)
            if absolute_url in seen:
                continue

            title = re.sub(r"\s+", " ", str(item.get("heading") or "")).strip()
            if len(title) < 8:
                continue

            published = self._parse_date(str(item.get("date") or ""))
            if published is not None and cutoff is not None and published < cutoff:
                if index == 0:
                    result.empty_reason = "listing_first_rgc_item_outside_time_window"
                    return
                break
            if published is not None and now_utc is not None and published > now_utc:
                continue

            seen.add(absolute_url)
            result.candidate_urls.append(absolute_url)
            result.candidate_titles[absolute_url] = title
            if published is not None:
                result.candidate_published_dates[absolute_url] = published

        if not result.candidate_urls:
            result.empty_reason = "no_rgc_news_links"

    @staticmethod
    def _parse_date(value: str) -> datetime.datetime | None:
        raw = (value or "").strip()
        if not raw:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(raw, fmt)
            except ValueError:
                continue
        return None
