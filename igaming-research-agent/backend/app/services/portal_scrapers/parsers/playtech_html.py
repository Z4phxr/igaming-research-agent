from __future__ import annotations

import datetime
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class PlaytechHtmlParser(PortalListingParser):
    """Parser for Playtech media press release listings."""

    _EXCLUDED_PATH_PARTS = (
        "/category/",
        "/about",
        "/services",
        "/products",
        "/locations",
        "/contact",
        "/privacy",
        "/further-policies",
        "/sustainable-success",
        "/investors",
        "/app/uploads/",
    )

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return "playtech.com/category/press-releases" in token_url or "playtech" in token_name

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
        links = soup.select("a[href*='playtech.com/'][href], a[href^='/'][href]")

        if not links:
            result.empty_reason = "no_playtech_release_links"
            return result

        seen: set[str] = set()
        for index, link in enumerate(links):
            href = str(link.get("href") or "").strip()
            absolute_url = urljoin(source_url, href)
            parsed = urlparse(absolute_url)
            path = (parsed.path or "").lower()

            if absolute_url in seen:
                continue
            if any(part in path for part in self._EXCLUDED_PATH_PARTS):
                continue
            # Press release URLs are slug-like article pages under root with hyphenated titles.
            if path.count("-") < 2:
                continue

            title = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
            if len(title) < 10:
                continue

            context_node = link.find_parent(["article", "li", "div"]) or link.parent
            context_text = re.sub(r"\s+", " ", context_node.get_text(" ", strip=True) if context_node else "").strip()
            published = self._parse_date(context_text)
            # Keep only true listing items; navigation/footer links do not carry press-release dates.
            if published is None:
                continue
            if published is not None and cutoff is not None and published < cutoff:
                if index == 0:
                    result.empty_reason = "listing_first_playtech_item_outside_time_window"
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
            result.empty_reason = "no_playtech_release_links"

        return result

    def is_likely_descending_chronological(self) -> bool:
        return True

    @staticmethod
    def _parse_date(value: str) -> datetime.datetime | None:
        match = re.search(r"\b(\d{1,2}\s+[A-Za-z]+\s+\d{4})\b", value or "")
        if not match:
            return None
        try:
            return datetime.datetime.strptime(match.group(1), "%d %B %Y")
        except ValueError:
            return None
