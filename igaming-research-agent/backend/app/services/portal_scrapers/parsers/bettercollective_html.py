from __future__ import annotations

import datetime
import json
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class BetterCollectiveHtmlParser(PortalListingParser):
    """Parser for Better Collective press releases listing."""

    _MFN_CONFIG_RE = re.compile(r"window\._MFN\s*=\s*(\{.*?\})\s*;", re.DOTALL)
    _MFN_FEED_ID_RE = re.compile(r"feed_id\s*[:=]\s*['\"]([0-9a-fA-F-]{36})['\"]", re.IGNORECASE)
    _MFN_SINGLE_VIEW_RE = re.compile(r"single_view_url\s*[:=]\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)

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

        dynamic_items = self._fetch_mfn_feed_items(html=html, source_url=source_url)
        if dynamic_items:
            self._append_dynamic_candidates(
                result=result,
                items=dynamic_items,
                source_url=source_url,
                cutoff=cutoff,
                now_utc=now_utc,
            )
            return result

        if not links:
            if self._is_bot_blocked(html):
                result.empty_reason = "bot_protection_blocked"
                return result
            if self._looks_like_dynamic_listing(html):
                result.empty_reason = "dynamic_listing_no_static_links"
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
            if self._looks_like_dynamic_listing(html):
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
            normalized = (value or "").strip()
            if normalized:
                candidates = [normalized]
                if normalized.endswith("Z"):
                    candidates.append(normalized[:-1] + "+00:00")
                for candidate in candidates:
                    try:
                        parsed = datetime.datetime.fromisoformat(candidate)
                        if parsed.tzinfo is not None:
                            return parsed.astimezone(datetime.timezone.utc).replace(tzinfo=None)
                        return parsed
                    except ValueError:
                        continue
            return None
        try:
            return datetime.datetime.strptime(match.group(1), "%d/%m/%Y")
        except ValueError:
            return None

    @classmethod
    def _extract_mfn_config(cls, html: str) -> dict:
        match = cls._MFN_CONFIG_RE.search(html or "")
        if not match:
            return {}
        raw = (match.group(1) or "").strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return parsed
        return {}

    def _fetch_mfn_feed_items(self, html: str, source_url: str) -> list[dict]:
        config = self._extract_mfn_config(html)
        if not config:
            loader_url = self._extract_mfn_loader_url(html=html, source_url=source_url)
            if loader_url:
                config = self._fetch_mfn_config_from_loader(loader_url=loader_url, source_url=source_url)
        feed_id = str(config.get("feed_id") or "").strip()
        if not feed_id:
            return []

        endpoint = "https://feed.mfn.se/compat/feed/all/a.json"
        params = {
            "type": "all",
            ".author.entity_id": feed_id,
            "limit": 15,
            "offset": 0,
        }

        try:
            response = requests.get(
                endpoint,
                params=params,
                timeout=20,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/json, text/plain, */*",
                    "Referer": source_url,
                },
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            return []

        items = payload.get("items") if isinstance(payload, dict) else None
        if not isinstance(items, list):
            return []

        return [item for item in items if isinstance(item, dict)]

    def _append_dynamic_candidates(
        self,
        result: ListingParseResult,
        items: list[dict],
        source_url: str,
        cutoff: datetime.datetime | None,
        now_utc: datetime.datetime | None,
    ) -> None:
        seen: set[str] = set()
        for index, item in enumerate(items):
            content = item.get("content") if isinstance(item, dict) else None
            if not isinstance(content, dict):
                continue

            slug = str(content.get("slug") or "").strip()
            if slug:
                absolute_url = urljoin(source_url, f"/press-releases/?slug={slug}")
            else:
                absolute_url = str(item.get("url") or "").strip()

            if not absolute_url or absolute_url in seen:
                continue

            title = re.sub(r"\s+", " ", str(content.get("title") or "")).strip()
            if len(title) < 8:
                continue

            published = self._parse_date(str(content.get("publish_date") or ""))
            if published is not None and cutoff is not None and published < cutoff:
                if index == 0:
                    result.empty_reason = "listing_first_bettercollective_item_outside_time_window"
                    return
                break
            if published is not None and now_utc is not None and published > now_utc:
                continue

            seen.add(absolute_url)
            result.candidate_urls.append(absolute_url)
            result.candidate_titles[absolute_url] = title
            if published is not None:
                result.candidate_published_dates[absolute_url] = published

        if not result.candidate_urls:
            result.empty_reason = "dynamic_listing_no_static_links"

    @staticmethod
    def _extract_mfn_loader_url(html: str, source_url: str) -> str:
        soup = BeautifulSoup(html or "", "html.parser")
        for script in soup.select("script[src]"):
            src = str(script.get("src") or "").strip()
            if not src:
                continue
            if "mfn-loader-news-landing-page.js" not in src.lower():
                continue
            return urljoin(source_url, src)
        return ""

    @classmethod
    def _fetch_mfn_config_from_loader(cls, loader_url: str, source_url: str) -> dict:
        try:
            response = requests.get(
                loader_url,
                timeout=20,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/javascript, text/javascript, */*",
                    "Referer": source_url,
                },
            )
            response.raise_for_status()
        except requests.RequestException:
            return {}

        text = response.text or ""
        config = cls._extract_mfn_config(text)
        if config:
            return config

        fallback: dict[str, str] = {}
        feed_match = cls._MFN_FEED_ID_RE.search(text)
        if feed_match:
            fallback["feed_id"] = feed_match.group(1)
        single_view_match = cls._MFN_SINGLE_VIEW_RE.search(text)
        if single_view_match:
            fallback["single_view_url"] = single_view_match.group(1)
        return fallback

    @staticmethod
    def _looks_like_dynamic_listing(html: str) -> bool:
        lower = (html or "").lower()
        return any(
            marker in lower
            for marker in (
                "window._mfn",
                "mfn-loader-news-landing-page.js",
                "feed.mfn.se",
            )
        )

    @staticmethod
    def _is_bot_blocked(html: str) -> bool:
        lower = (html or "").lower()
        signals = [
            "cf-chl-",
            "cf-browser-verification",
            "challenge-platform",
            "attention required",
            "please enable cookies",
            "captcha",
            "access denied",
        ]
        return any(signal in lower for signal in signals)
