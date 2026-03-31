from __future__ import annotations

import datetime
import html
import json
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class GdcGroupHtmlParser(PortalListingParser):
    """Parser for Gambling.com Group media center listings."""

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return "gdcgroup.com/media-center" in token_url or "gambling.com group" in token_name

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
        soup = BeautifulSoup(html, "html.parser")
        links = soup.select("a[href*='/media-center/'][href]")

        payload_items = self._extract_articles_payload(soup, html)
        if payload_items:
            self._append_payload_candidates(
                result=result,
                items=payload_items,
                source_url=source_url,
                cutoff=cutoff,
                now_utc=now_utc,
            )
            return result

        if not links:
            if self._is_bot_blocked(html):
                result.empty_reason = "bot_protection_blocked"
                return result
            result.empty_reason = "no_gdcgroup_release_links"
            return result

        seen: set[str] = set()
        for index, link in enumerate(links):
            href = str(link.get("href") or "").strip()
            absolute_url = urljoin(source_url, href)
            path = (urlparse(absolute_url).path or "").lower().strip("/")
            if absolute_url in seen:
                continue
            if path == "media-center" or path.startswith("investors/"):
                continue

            title = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
            if len(title) < 8:
                continue

            context_node = link.find_parent(["article", "li", "div"]) or link.parent
            context_text = re.sub(r"\s+", " ", context_node.get_text(" ", strip=True) if context_node else "").strip()
            published = self._parse_date(context_text)
            if published is not None and cutoff is not None and published < cutoff:
                if index == 0:
                    result.empty_reason = "listing_first_gdcgroup_item_outside_time_window"
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
            result.empty_reason = "no_gdcgroup_release_links"

        return result

    def is_likely_descending_chronological(self) -> bool:
        return True

    @staticmethod
    def _parse_date(value: str) -> datetime.datetime | None:
        match = re.search(r"\b([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th),\s+\d{4})\b", value or "", re.IGNORECASE)
        if not match:
            return None
        cleaned = re.sub(r"(\d)(st|nd|rd|th)", r"\1", match.group(1), flags=re.IGNORECASE)
        try:
            return datetime.datetime.strptime(cleaned, "%B %d, %Y")
        except ValueError:
            return None

    @staticmethod
    def _extract_articles_payload(soup: BeautifulSoup, raw_html: str) -> list[dict]:
        component = soup.find("news-articles-component")
        payload = ""
        if component is not None:
            payload = str(component.get(":articles") or "").strip()
            if not payload:
                payload = str(component.get("articles") or "").strip()

        if not payload:
            match = re.search(r"<news-articles-component[^>]+:articles=\"([^\"]+)\"", raw_html or "", re.IGNORECASE)
            if match:
                payload = match.group(1).strip()

        if not payload:
            return []

        decoded_payload = html.unescape(payload)
        try:
            parsed = json.loads(decoded_payload)
        except (json.JSONDecodeError, TypeError):
            return []

        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
        return []

    def _append_payload_candidates(
        self,
        result: ListingParseResult,
        items: list[dict],
        source_url: str,
        cutoff: datetime.datetime | None,
        now_utc: datetime.datetime | None,
    ) -> None:
        for index, item in enumerate(items):
            href = str(item.get("article_url") or "").strip()
            if not href:
                continue
            absolute_url = urljoin(source_url, href)

            title = re.sub(r"\s+", " ", str(item.get("page_title") or "")).strip()
            if len(title) < 8:
                continue

            published = self._parse_date(str(item.get("publish_date") or ""))
            if published is not None and cutoff is not None and published < cutoff:
                if index == 0:
                    result.empty_reason = "listing_first_gdcgroup_item_outside_time_window"
                    return
                break
            if published is not None and now_utc is not None and published > now_utc:
                continue

            result.candidate_urls.append(absolute_url)
            result.candidate_titles[absolute_url] = title
            if published is not None:
                result.candidate_published_dates[absolute_url] = published

        if not result.candidate_urls:
            result.empty_reason = "no_gdcgroup_release_links"

    @staticmethod
    def _is_bot_blocked(html: str) -> bool:
        lower = (html or "").lower()
        signals = [
            "cf-chl-",
            "cf-browser-verification",
            "challenge-platform",
            "attention required",
            "please enable cookies",
            "captcha",
            "access denied",
        ]
        return any(signal in lower for signal in signals)
