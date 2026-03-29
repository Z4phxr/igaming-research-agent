from __future__ import annotations

import datetime
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


@dataclass(frozen=True)
class HtmlListingParserConfig:
    name: str
    source_url_contains: tuple[str, ...] = ()
    company_name_contains: tuple[str, ...] = ()
    item_selector: str = ""
    link_selector: str = "a[href]"
    title_selector: str | None = None
    date_selector: str | None = None
    date_formats: tuple[str, ...] = ()
    scope_selector: str | None = None
    link_href_must_contain: tuple[str, ...] = ()
    link_href_excludes: tuple[str, ...] = ()
    blocked_markers: tuple[str, ...] = ()
    empty_reason_blocked: str = "bot_protection_blocked"
    descending_chronological: bool = False
    empty_reason_no_items: str = "no_config_items_found"


class ConfigDrivenHtmlParser(PortalListingParser):
    """Generic parser driven by per-source CSS selector configuration."""

    def __init__(self, configs: list[HtmlListingParserConfig]):
        self._configs = list(configs)

    def matches(self, source_url: str, company_name: str) -> bool:
        return self._select_config(source_url=source_url, company_name=company_name) is not None

    def parse_listing(
        self,
        listing_html: str,
        source_url: str,
        company_name: str,
        cutoff: datetime.datetime | None = None,
        now_utc: datetime.datetime | None = None,
    ) -> ListingParseResult:
        result = ListingParseResult()
        config = self._select_config(source_url=source_url, company_name=company_name)
        if config is None:
            result.empty_reason = "no_matching_config"
            return result

        soup = BeautifulSoup(listing_html or "", "html.parser")
        scope = soup
        if config.scope_selector:
            scoped = soup.select_one(config.scope_selector)
            if scoped is None:
                result.empty_reason = "scope_not_found"
                return result
            scope = scoped

        items = scope.select(config.item_selector)
        if not items:
            page_text = (listing_html or "").lower()
            if any(marker.lower() in page_text for marker in config.blocked_markers):
                result.empty_reason = config.empty_reason_blocked
                return result
            result.empty_reason = config.empty_reason_no_items
            return result

        seen: set[str] = set()
        for index, item in enumerate(items):
            link_node = item.select_one(config.link_selector)
            if link_node is None and getattr(item, "name", "") == "a" and item.get("href"):
                link_node = item
            href = ""
            if link_node is not None:
                href = str(link_node.get("href") or "").strip()

            href_lower = href.lower()
            if config.link_href_must_contain and not any(
                token.lower() in href_lower for token in config.link_href_must_contain
            ):
                continue
            if config.link_href_excludes and any(
                token.lower() in href_lower for token in config.link_href_excludes
            ):
                continue

            absolute_url = urljoin(source_url, href)
            if not href or not absolute_url or absolute_url in seen:
                continue
            if _same_effective_url(absolute_url, source_url):
                continue

            title = ""
            if config.title_selector:
                title_node = item.select_one(config.title_selector)
                if title_node is not None:
                    title = _clean_text(title_node.get_text(" ", strip=True))
            if not title and link_node is not None:
                title = _clean_text(link_node.get_text(" ", strip=True))

            published = None
            if config.date_selector:
                date_node = item.select_one(config.date_selector)
                raw_date = _clean_text(date_node.get_text(" ", strip=True)) if date_node is not None else ""
                published = _parse_date(raw_date, config.date_formats)

            if published is not None and cutoff is not None and published < cutoff:
                if index == 0:
                    result.empty_reason = "listing_first_item_outside_time_window"
                    return result
                if config.descending_chronological:
                    break
                continue

            if published is not None and now_utc is not None and published > now_utc:
                continue

            seen.add(absolute_url)
            result.candidate_urls.append(absolute_url)
            if title:
                result.candidate_titles[absolute_url] = title
            if published is not None:
                result.candidate_published_dates[absolute_url] = published

        if not result.candidate_urls and result.empty_reason is None:
            result.empty_reason = "no_in_window_items"

        return result

    def is_likely_descending_chronological(self) -> bool:
        # Keep behavior conservative for parser-level API; ordering is config-specific in parse_listing.
        return False

    def _select_config(self, source_url: str, company_name: str) -> HtmlListingParserConfig | None:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()

        for config in self._configs:
            url_match = any(piece.lower() in token_url for piece in config.source_url_contains)
            name_match = any(piece.lower() in token_name for piece in config.company_name_contains)
            if url_match or name_match:
                return config
        return None


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _same_effective_url(left: str, right: str) -> bool:
    a = urlsplit((left or "").strip())
    b = urlsplit((right or "").strip())
    a_host = (a.netloc or "").lower().lstrip("www.")
    b_host = (b.netloc or "").lower().lstrip("www.")
    a_path = (a.path or "").rstrip("/")
    b_path = (b.path or "").rstrip("/")
    return a_host == b_host and a_path == b_path


def _parse_date(raw: str, formats: tuple[str, ...]) -> datetime.datetime | None:
    value = (raw or "").strip()
    if not value:
        return None
    normalized = re.sub(r"\s+", "", value)
    for fmt in formats:
        for candidate in (value, normalized):
            try:
                return datetime.datetime.strptime(candidate, fmt)
            except ValueError:
                continue
    return None
