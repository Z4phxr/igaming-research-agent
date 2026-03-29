from __future__ import annotations

import datetime
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class PragmaticPlayHtmlParser(PortalListingParser):
    """Parser for Pragmatic Play news listing pages."""

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return "pragmaticplay.com/en/news" in token_url or "pragmatic play" in token_name

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
        links = soup.select("a[href*='/en/news/'][href]:not([href$='/en/news/'])")

        if not links:
            lower_html = html.lower()
            if "/en/news/page/" in lower_html and "latest news and events" in lower_html:
                result.empty_reason = "dynamic_listing_no_static_links"
                return result
            result.empty_reason = "no_pragmaticplay_release_links"
            return result

        seen: set[str] = set()
        for index, link in enumerate(links):
            href = str(link.get("href") or "").strip()
            absolute_url = urljoin(source_url, href)
            path = (urlparse(absolute_url).path or "").lower()
            if absolute_url in seen or path.endswith("/en/news/"):
                continue

            title = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
            if len(title) < 10:
                continue

            context_node = link.find_parent(["article", "li", "div"]) or link.parent
            context_text = re.sub(r"\s+", " ", context_node.get_text(" ", strip=True) if context_node else "").strip()
            published = self._parse_date(context_text)
            if published is not None and cutoff is not None and published < cutoff:
                if index == 0:
                    result.empty_reason = "listing_first_pragmaticplay_item_outside_time_window"
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
            result.empty_reason = "no_pragmaticplay_release_links"

        return result

    def is_likely_descending_chronological(self) -> bool:
        return True

    @staticmethod
    def _parse_date(value: str) -> datetime.datetime | None:
        match = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)\s+([A-Za-z]{3})\s+(\d{4})\b", value or "", re.IGNORECASE)
        if not match:
            return None
        try:
            day = int(match.group(1))
            month = datetime.datetime.strptime(match.group(2).title(), "%b").month
            year = int(match.group(3))
            return datetime.datetime(year, month, day)
        except ValueError:
            return None
