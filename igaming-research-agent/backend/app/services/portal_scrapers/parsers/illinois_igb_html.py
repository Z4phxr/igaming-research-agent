from __future__ import annotations

import datetime
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class IllinoisIgbHtmlParser(PortalListingParser):
    """Parser for Illinois Gaming Board press-release listing pages."""

    _ABS_RELEASE_RE = re.compile(r"https?://www\.illinois\.gov/news/press-release\.\d+\.html", re.IGNORECASE)
    _REL_RELEASE_RE = re.compile(r"/news/press-release\.\d+\.html", re.IGNORECASE)
    _REL_RELEASE_ESC_RE = re.compile(r"\\/news\\/press-release\.\d+\.html", re.IGNORECASE)
    _ABS_ADDITIONAL_PDF_RE = re.compile(
        r"https?://igb\.illinois\.gov/content/dam/soi/en/web/igb/documents/press-releases/additional-news/[^\"'\s]+\.pdf",
        re.IGNORECASE,
    )
    _REL_ADDITIONAL_PDF_RE = re.compile(
        r"/content/dam/soi/en/web/igb/documents/press-releases/additional-news/[^\"'\s]+\.pdf",
        re.IGNORECASE,
    )
    _REL_ADDITIONAL_PDF_ESC_RE = re.compile(
        r"\\/content\\/dam\\/soi\\/en\\/web\\/igb\\/documents\\/press-releases\\/additional-news\\/[^\"\s]+\.pdf",
        re.IGNORECASE,
    )

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return "igb.illinois.gov/news/press-releases" in token_url or "illinois gaming board" in token_name

    def parse_listing(
        self,
        listing_html: str,
        source_url: str,
        company_name: str,
        cutoff: datetime.datetime | None = None,
        now_utc: datetime.datetime | None = None,
    ) -> ListingParseResult:
        del cutoff, now_utc

        html = listing_html or ""
        result = ListingParseResult()
        soup = BeautifulSoup(html, "html.parser")

        seen: set[str] = set()

        for link in soup.select("a[href*='illinois.gov/news/press-release.'], a[href*='/news/press-release.'], a[href*='/documents/press-releases/']"):
            href = str(link.get("href") or "").strip()
            if not href:
                continue
            absolute_url = urljoin(source_url, href)
            if absolute_url in seen:
                continue
            if not self._looks_like_release_href(absolute_url):
                continue

            title = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
            seen.add(absolute_url)
            result.candidate_urls.append(absolute_url)
            if title and len(title) >= 8:
                result.candidate_titles[absolute_url] = title

        if not result.candidate_urls:
            # Dynamic templates can still embed final URLs in JSON chunks/script payloads.
            for matched in self._ABS_RELEASE_RE.findall(html):
                if matched not in seen:
                    seen.add(matched)
                    result.candidate_urls.append(matched)
            for matched in self._ABS_ADDITIONAL_PDF_RE.findall(html):
                if matched not in seen:
                    seen.add(matched)
                    result.candidate_urls.append(matched)
            for matched in self._REL_RELEASE_RE.findall(html):
                absolute = urljoin(source_url, matched)
                if absolute not in seen:
                    seen.add(absolute)
                    result.candidate_urls.append(absolute)
            for matched in self._REL_ADDITIONAL_PDF_RE.findall(html):
                absolute = urljoin(source_url, matched)
                if absolute not in seen:
                    seen.add(absolute)
                    result.candidate_urls.append(absolute)
            for matched in self._REL_RELEASE_ESC_RE.findall(html):
                normalized = matched.replace("\\/", "/")
                absolute = urljoin(source_url, normalized)
                if absolute not in seen:
                    seen.add(absolute)
                    result.candidate_urls.append(absolute)
            for matched in self._REL_ADDITIONAL_PDF_ESC_RE.findall(html):
                normalized = matched.replace("\\/", "/")
                absolute = urljoin(source_url, normalized)
                if absolute not in seen:
                    seen.add(absolute)
                    result.candidate_urls.append(absolute)

        if not result.candidate_urls:
            lower = html.lower()
            if "news_feed.model.json" in lower and "{{this.url}}" in lower:
                result.empty_reason = "dynamic_listing_no_static_links"
            else:
                result.empty_reason = "no_igb_press_release_links"

        return result

    def extract_article_published_date(self, article_html: str):
        html = article_html or ""

        # Common machine-readable dates.
        for pattern in (
            r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+name=["\']datePublished["\'][^>]+content=["\']([^"\']+)["\']',
            r'"datePublished"\s*:\s*"([^"\\]+)"',
        ):
            match = re.search(pattern, html, flags=re.IGNORECASE)
            if not match:
                continue
            parsed = self._parse_datetime(match.group(1).strip())
            if parsed is not None:
                return parsed

        text = re.sub(r"\s+", " ", BeautifulSoup(html, "html.parser").get_text(" ", strip=True))

        weekday_match = re.search(
            r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})\b",
            text,
        )
        if weekday_match:
            try:
                return datetime.datetime.strptime(weekday_match.group(1), "%B %d, %Y")
            except ValueError:
                pass

        generic_match = re.search(r"\b([A-Za-z]+\s+\d{1,2},\s+\d{4})\b", text)
        if generic_match:
            try:
                return datetime.datetime.strptime(generic_match.group(1), "%B %d, %Y")
            except ValueError:
                return None

        return None

    def is_likely_descending_chronological(self) -> bool:
        return True

    @staticmethod
    def _looks_like_release_href(url: str) -> bool:
        lower = (url or "").lower()
        return (
            "illinois.gov/news/press-release." in lower
            or "/documents/press-releases/" in lower
            or lower.endswith(".pdf")
        )

    @staticmethod
    def _parse_datetime(value: str) -> datetime.datetime | None:
        raw = (value or "").strip()
        if not raw:
            return None

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

        for fmt in ("%m/%d/%Y %H:%M:%S", "%B %d, %Y"):
            try:
                return datetime.datetime.strptime(raw, fmt)
            except ValueError:
                continue

        return None
