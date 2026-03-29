from __future__ import annotations

import datetime
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class AristocratHtmlParser(PortalListingParser):
    """Dedicated parser for Aristocrat news listing."""

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return "aristocrat.com/news" in token_url or "aristocrat" in token_name

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
        articles = soup.select("article")

        if not articles:
            result.empty_reason = "no_aristocrat_articles"
            return result

        seen: set[str] = set()
        for index, article in enumerate(articles):
            link = article.select_one("a[href]")
            if link is None:
                continue
            href = str(link.get("href") or "").strip()
            absolute_url = urljoin(source_url, href)
            if "/news/" in absolute_url.rstrip("/").lower() and absolute_url.rstrip("/").lower().endswith("/news"):
                continue
            if absolute_url in seen:
                continue

            title = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
            if not title:
                continue

            published = self._extract_date(article)
            if published is not None and cutoff is not None and published < cutoff:
                if index == 0:
                    result.empty_reason = "listing_first_aristocrat_item_outside_time_window"
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
            result.empty_reason = "no_aristocrat_in_window_links"

        return result

    def is_likely_descending_chronological(self) -> bool:
        return True

    @staticmethod
    def _extract_date(article) -> datetime.datetime | None:
        text = re.sub(r"\s+", " ", article.get_text(" ", strip=True)).strip()
        match = re.search(r"\b([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})\b", text)
        if not match:
            return None
        try:
            return datetime.datetime.strptime(match.group(1), "%b %d, %Y")
        except ValueError:
            return None
