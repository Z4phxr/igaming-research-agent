from __future__ import annotations

import datetime
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class IgtHtmlParser(PortalListingParser):
    """Dedicated parser for IGT news listing."""

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return "igt.com/explore-igt/news/news" in token_url or token_name.startswith("igt")

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
        links = soup.select("a[href*='News Room Details?Index=']")

        if not links:
            result.empty_reason = "no_igt_release_links"
            return result

        seen: set[str] = set()
        for index, link in enumerate(links):
            href = str(link.get("href") or "").strip()
            absolute_url = urljoin(source_url, href)
            if absolute_url in seen:
                continue

            text = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
            if not text:
                continue
            published = self._parse_trailing_mmddyyyy(text)
            title = text
            if published is not None:
                title = re.sub(r"\s+\d{2}/\d{2}/\d{4}$", "", text).strip()

            if published is not None and cutoff is not None and published < cutoff:
                if index == 0:
                    result.empty_reason = "listing_first_igt_item_outside_time_window"
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
            result.empty_reason = "no_igt_in_window_links"

        return result

    def is_likely_descending_chronological(self) -> bool:
        return True

    @staticmethod
    def _parse_trailing_mmddyyyy(value: str) -> datetime.datetime | None:
        match = re.search(r"\b(\d{2}/\d{2}/\d{4})\b$", value or "")
        if not match:
            return None
        try:
            return datetime.datetime.strptime(match.group(1), "%m/%d/%Y")
        except ValueError:
            return None
