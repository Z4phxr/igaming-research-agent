from __future__ import annotations

import datetime
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class PragmaticPlayHtmlParser(PortalListingParser):
    """Parser for Pragmatic Play news listing pages."""

    _ONCLICK_HREF_RE = re.compile(r"hrefTo\((['\"])(?P<url>.+?)\1\)", re.IGNORECASE)

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

        card_items: list[dict[str, object]] = []
        for card in soup.select("div.news div.news__box-white[onclick], div.news__box-white[onclick]"):
            onclick_value = str(card.get("onclick") or "").strip()
            if not onclick_value:
                continue

            match = self._ONCLICK_HREF_RE.search(onclick_value)
            if not match:
                continue

            href = match.group("url").strip()
            if not href:
                continue

            absolute_url = urljoin(source_url, href)
            path = (urlparse(absolute_url).path or "").lower()
            if path.endswith("/en/news"):
                continue

            title_node = card.select_one("h3.news__title")
            title = re.sub(r"\s+", " ", title_node.get_text(" ", strip=True) if title_node else "").strip()
            if len(title) < 10:
                continue

            date_node = card.select_one("p.news__date")
            date_text = re.sub(r"\s+", " ", date_node.get_text(" ", strip=True) if date_node else "").strip()
            published = self._parse_date(date_text)

            card_items.append({"url": absolute_url, "title": title, "published": published})

        if card_items:
            seen_cards: set[str] = set()
            for index, item in enumerate(card_items):
                absolute_url = str(item["url"])
                if absolute_url in seen_cards:
                    continue

                published = item.get("published")
                if isinstance(published, datetime.datetime) and cutoff is not None and published < cutoff:
                    if index == 0:
                        result.empty_reason = "listing_first_pragmaticplay_item_outside_time_window"
                        return result
                    break

                if isinstance(published, datetime.datetime) and now_utc is not None and published > now_utc:
                    continue

                seen_cards.add(absolute_url)
                result.candidate_urls.append(absolute_url)
                result.candidate_titles[absolute_url] = str(item.get("title") or "")
                if isinstance(published, datetime.datetime):
                    result.candidate_published_dates[absolute_url] = published

            if result.candidate_urls:
                return result

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
