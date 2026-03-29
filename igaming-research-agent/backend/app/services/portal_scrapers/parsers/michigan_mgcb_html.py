from __future__ import annotations

import datetime
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class MichiganMgcbHtmlParser(PortalListingParser):
    """Parser for Michigan Gaming Control Board listing and article pages."""

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return "michigan.gov/mgcb/news" in token_url or "michigan gaming control board" in token_name

    def parse_listing(
        self,
        listing_html: str,
        source_url: str,
        company_name: str,
        cutoff: datetime.datetime | None = None,
        now_utc: datetime.datetime | None = None,
    ) -> ListingParseResult:
        del cutoff, now_utc

        result = ListingParseResult()
        html = listing_html or ""
        soup = BeautifulSoup(html, "html.parser")

        cards = soup.select("div.com-wrapper div.related-content__section-content")
        if not cards:
            if "access denied" in html.lower() or "forbidden" in html.lower() or "captcha" in html.lower():
                result.empty_reason = "bot_protection_blocked"
                return result
            result.empty_reason = "no_mgcb_news_cards"
            return result

        seen: set[str] = set()
        for card in cards:
            link = card.select_one("a[href*='/mgcb/news/']")
            if link is None:
                continue

            href = str(link.get("href") or "").strip()
            absolute_url = urljoin(source_url, href)
            normalized = absolute_url.rstrip("/").lower()
            if normalized in {"https://www.michigan.gov/mgcb/news", "https://michigan.gov/mgcb/news"}:
                continue
            if absolute_url in seen:
                continue

            title_node = link.select_one("h3")
            title_raw = title_node.get_text(" ", strip=True) if title_node is not None else link.get_text(" ", strip=True)
            title = re.sub(r"\s+", " ", title_raw).strip()
            if len(title) < 8:
                continue

            seen.add(absolute_url)
            result.candidate_urls.append(absolute_url)
            result.candidate_titles[absolute_url] = title

        if not result.candidate_urls:
            result.empty_reason = "no_mgcb_news_links"

        return result

    def extract_article_published_date(self, article_html: str):
        html = article_html or ""
        match = re.search(
            r'<meta[^>]+name=["\']datePublished["\'][^>]+content=["\']([^"\']+)["\']',
            html,
            flags=re.IGNORECASE,
        )
        if not match:
            return None

        raw = match.group(1).strip()
        for fmt in ("%m/%d/%Y %H:%M:%S", "%m/%d/%y %H:%M:%S"):
            try:
                return datetime.datetime.strptime(raw, fmt)
            except ValueError:
                continue
        return None

    def is_likely_descending_chronological(self) -> bool:
        return True
