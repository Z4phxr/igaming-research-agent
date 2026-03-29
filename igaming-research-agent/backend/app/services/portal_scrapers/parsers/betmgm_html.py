from __future__ import annotations

import datetime
import re
from urllib.parse import urljoin

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class BetMgmHtmlParser(PortalListingParser):
    """Dedicated parser for BetMGM news tiles on sports.betmgm.com blog pages."""

    _TILE_PATTERN = re.compile(
        r'<div[^>]*class="[^"]*news-tile[^"]*long-news-tile[^"]*"[^>]*>'
        r'.*?<h3>\s*<a[^>]+href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>'
        r'.*?<span[^>]*class="[^"]*tile-date[^"]*"[^>]*>(?P<date>[^<]+)</span>',
        flags=re.IGNORECASE | re.DOTALL,
    )
    _LATEST_STORIES_HEADING = re.compile(
        r'<h2[^>]*>\s*Latest\s+Stories\s*</h2>',
        flags=re.IGNORECASE | re.DOTALL,
    )
    _SF_POSTS_OPEN = re.compile(r'<div[^>]*id="sf-posts"[^>]*>', flags=re.IGNORECASE)
    _DIV_TAG = re.compile(r'</?div\b[^>]*>', flags=re.IGNORECASE)

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return "sports.betmgm.com" in token_url or "betmgm" in token_name

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
        scoped_html = self._extract_latest_stories_scope(html)
        if scoped_html is None:
            result.empty_reason = "no_latest_stories_section"
            return result

        html = scoped_html
        tiles = list(self._TILE_PATTERN.finditer(html))

        if not tiles:
            result.empty_reason = "no_news_tiles_found"
            return result

        seen: set[str] = set()
        for index, match in enumerate(tiles):
            href = (match.group("href") or "").strip()
            title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", match.group("title") or "")).strip()
            raw_date = re.sub(r"\s+", " ", (match.group("date") or "")).strip()
            published = self._parse_tile_date(raw_date)
            absolute_url = urljoin(source_url, href)

            if published is not None and cutoff is not None and published < cutoff:
                if index == 0:
                    result.empty_reason = "listing_first_tile_outside_time_window"
                    return result
                # Tiles are newest -> oldest, so stale means everything below is stale too.
                break

            if published is not None and now_utc is not None and published > now_utc:
                continue

            if not absolute_url or absolute_url in seen:
                continue
            seen.add(absolute_url)
            result.candidate_urls.append(absolute_url)
            if title:
                result.candidate_titles[absolute_url] = title
            if published is not None:
                result.candidate_published_dates[absolute_url] = published

        if not result.candidate_urls and result.empty_reason is None:
            result.empty_reason = "no_in_window_tiles"

        return result

    def is_likely_descending_chronological(self) -> bool:
        return True

    @staticmethod
    def _parse_tile_date(raw: str) -> datetime.datetime | None:
        value = (raw or "").strip()
        if not value:
            return None
        try:
            return datetime.datetime.strptime(value, "%b %d, %Y")
        except ValueError:
            return None

    def _extract_latest_stories_scope(self, html: str) -> str | None:
        heading_match = self._LATEST_STORIES_HEADING.search(html or "")
        search_start = heading_match.end() if heading_match is not None else 0
        suffix = html[search_start:]
        sf_posts_match = self._SF_POSTS_OPEN.search(suffix)
        if sf_posts_match is None:
            if heading_match is None:
                return None
            return suffix

        start = search_start + sf_posts_match.start()
        open_match = self._SF_POSTS_OPEN.search(html, pos=start)
        if open_match is None:
            return suffix

        depth = 0
        first_seen = False
        for div_match in self._DIV_TAG.finditer(html, pos=open_match.start()):
            token = div_match.group(0)
            is_close = token.startswith("</")
            if not is_close:
                depth += 1
                first_seen = True
            elif first_seen:
                depth -= 1
                if depth == 0:
                    return html[open_match.start() : div_match.end()]

        return html[open_match.start() :]
