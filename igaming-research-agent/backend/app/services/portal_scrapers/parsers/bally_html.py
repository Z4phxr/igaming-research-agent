from __future__ import annotations

import datetime
import re
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class BallyHtmlParser(PortalListingParser):
    """Parser for Bally's investor/news pages (Q4-hosted)."""

    _Q4_CATEGORY_RE = re.compile(r"category\s*:\s*'([0-9a-fA-F-]{36})'")

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return "ballys.com/news/default.aspx" in token_url or "bally" in token_name

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
        lower_html = html.lower()

        if "auth.platform.q4inc.com/auth" in lower_html or "error=login_required" in lower_html:
            result.empty_reason = "q4_auth_required"
            return result

        soup = BeautifulSoup(html, "html.parser")
        links = soup.select("a[href*='/news-releases/news-release-details/'], a[href*='/news/news-details/']")
        if not links:
            dynamic_items = self._fetch_q4_public_feed_items(source_url=source_url, listing_html=html)
            if dynamic_items:
                seen_dynamic: set[str] = set()
                for index, item in enumerate(dynamic_items):
                    absolute_url = item["url"]
                    if absolute_url in seen_dynamic:
                        continue

                    published = item.get("published")
                    if published is not None and cutoff is not None and published < cutoff:
                        if index == 0:
                            result.empty_reason = "listing_first_bally_item_outside_time_window"
                            return result
                        break

                    if published is not None and now_utc is not None and published > now_utc:
                        continue

                    seen_dynamic.add(absolute_url)
                    result.candidate_urls.append(absolute_url)
                    title = item.get("title")
                    if title:
                        result.candidate_titles[absolute_url] = title
                    if published is not None:
                        result.candidate_published_dates[absolute_url] = published

                if result.candidate_urls:
                    return result

            if self._looks_like_dynamic_q4_news_widget(lower_html):
                result.empty_reason = "q4_dynamic_listing_no_static_links"
                return result
            result.empty_reason = "no_bally_release_links"
            return result

        seen: set[str] = set()
        for index, link in enumerate(links):
            href = str(link.get("href") or "").strip()
            absolute_url = urljoin(source_url, href)
            if absolute_url in seen:
                continue
            title = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
            if not title:
                continue

            published = self._extract_nearby_date(link)
            if published is not None and cutoff is not None and published < cutoff:
                if index == 0:
                    result.empty_reason = "listing_first_bally_item_outside_time_window"
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
            result.empty_reason = "no_bally_release_links"

        return result

    def is_likely_descending_chronological(self) -> bool:
        return True

    @staticmethod
    def _looks_like_dynamic_q4_news_widget(lower_html: str) -> bool:
        return any(
            marker in lower_html
            for marker in (
                "evergreen evergreen-news",
                "evergreen.q4api",
                "$('.module-news",
                ".news({",
                "id=\"newslist\"",
                "module_headline-link",
            )
        )

    @staticmethod
    def _extract_nearby_date(link) -> datetime.datetime | None:
        row = link.find_parent("tr")
        if row is not None:
            time_node = row.select_one("time")
            if time_node is not None:
                parsed = BallyHtmlParser._parse_q4_date(time_node.get_text(" ", strip=True))
                if parsed is not None:
                    return parsed

        parent_text = re.sub(r"\s+", " ", link.parent.get_text(" ", strip=True) if link.parent else "").strip()
        return BallyHtmlParser._parse_q4_date(parent_text)

    def _fetch_q4_public_feed_items(self, source_url: str, listing_html: str) -> list[dict[str, object]]:
        match = self._Q4_CATEGORY_RE.search(listing_html or "")
        category_id = match.group(1) if match else None

        split = urlsplit(source_url)
        base_url = f"{split.scheme}://{split.netloc}" if split.scheme and split.netloc else source_url
        feed_urls = (
            urljoin(base_url, "/feed/PressRelease.svc/GetPressReleaseList"),
            urljoin(base_url, "/Services/PressReleaseService.svc/GetPressReleaseList"),
        )

        for feed_url in feed_urls:
            params = {
                "LanguageId": 1,
                "pressReleaseDateFilter": 3,
                "bodyType": 0,
            }
            if category_id:
                params["categoryId"] = category_id

            try:
                response = requests.get(
                    feed_url,
                    params=params,
                    timeout=20,
                    headers={
                        "User-Agent": "Mozilla/5.0",
                        "Accept": "application/json, text/javascript, */*; q=0.01",
                        "X-Requested-With": "XMLHttpRequest",
                        "Referer": source_url,
                    },
                )
                response.raise_for_status()
                payload = response.json()
            except (requests.RequestException, ValueError):
                continue

            rows = payload.get("GetPressReleaseListResult") if isinstance(payload, dict) else None
            if not isinstance(rows, list):
                continue

            items: list[dict[str, object]] = []
            for row in rows:
                if not isinstance(row, dict):
                    continue

                href = str(row.get("LinkToDetailPage") or row.get("LinkToUrl") or "").strip()
                if not href:
                    continue

                absolute_url = urljoin(base_url, href.replace("\\/", "/"))
                if absolute_url.rstrip("/").lower() == source_url.rstrip("/").lower():
                    continue

                title = re.sub(r"\s+", " ", str(row.get("Headline") or "").strip())
                published = self._parse_q4_date(str(row.get("PressReleaseDate") or "").strip())
                items.append({"url": absolute_url, "title": title, "published": published})

            if items:
                return items

        return []

    @staticmethod
    def _parse_q4_date(value: str) -> datetime.datetime | None:
        raw = (value or "").strip()
        if not raw:
            return None

        for fmt in ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.datetime.strptime(raw, fmt)
            except ValueError:
                continue

        candidates = [raw]
        if raw.endswith("Z"):
            candidates.append(raw[:-1] + "+00:00")

        for candidate in candidates:
            try:
                parsed = datetime.datetime.fromisoformat(candidate)
                if parsed.tzinfo is not None:
                    return parsed.astimezone(datetime.timezone.utc).replace(tzinfo=None)
                return parsed
            except ValueError:
                continue

        return None
