from __future__ import annotations

import datetime
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class BetterCollectiveHtmlParser(PortalListingParser):
    """Parser for Better Collective press releases listing."""

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return "bettercollective.com/press-releases" in token_url or "better collective" in token_name

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
        links = soup.select("a[href*='bettercollective.com'][href], a[href^='/'][href]")

        if not links:
            if self._is_bot_blocked(html):
                result.empty_reason = "bot_protection_blocked"
                return result
            result.empty_reason = "no_bettercollective_release_links"
            return result

        seen: set[str] = set()
        for index, link in enumerate(links):
            href = str(link.get("href") or "").strip()
            absolute_url = urljoin(source_url, href)
            lower = absolute_url.lower().rstrip("/")
            path = (urlparse(absolute_url).path or "").lower().strip("/")
            if absolute_url in seen:
                continue
            if path == "press-releases" or "/investors/" in lower or lower.endswith(".pdf"):
                continue
            if "press-releases/" not in path:
                continue

            title = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
            if len(title) < 8:
                continue

            context_node = link.find_parent(["article", "li", "div"]) or link.parent
            context_text = re.sub(r"\s+", " ", context_node.get_text(" ", strip=True) if context_node else "").strip()
            published = self._parse_date(context_text)
            if published is not None and cutoff is not None and published < cutoff:
                if index == 0:
                    result.empty_reason = "listing_first_bettercollective_item_outside_time_window"
                    return result
                break
            if published is not None and now_utc is not None and published > now_utc:
                continue

            seen.add(absolute_url)
            result.candidate_urls.append(absolute_url)
            result.candidate_titles[absolute_url] = title
            if published is not None:
                result.candidate_published_dates[absolute_url] = published

        if not result.candidate_urls:
            if self._is_bot_blocked(html):
                result.empty_reason = "bot_protection_blocked"
                return result
            if re.search(r"\b\d{2}/\d{2}/\d{4},\s*\d{2}:\d{2}:\d{2}\b", html):
                result.empty_reason = "dynamic_listing_no_static_links"
            else:
                result.empty_reason = "no_bettercollective_release_links"

        return result

    def is_likely_descending_chronological(self) -> bool:
        return True

    @staticmethod
    def _parse_date(value: str) -> datetime.datetime | None:
        match = re.search(r"\b(\d{2}/\d{2}/\d{4}),\s*\d{2}:\d{2}:\d{2}\b", value or "")
        if not match:
            return None
        try:
            return datetime.datetime.strptime(match.group(1), "%d/%m/%Y")
        except ValueError:
            return None

    @staticmethod
    def _is_bot_blocked(html: str) -> bool:
        lower = (html or "").lower()
        return "cloudflare" in lower or "captcha" in lower or "bot" in lower or "access denied" in lower
