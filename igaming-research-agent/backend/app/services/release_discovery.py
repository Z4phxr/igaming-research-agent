"""Discover company release links from configured source pages."""

import datetime
import logging
import re
from urllib.parse import urljoin, urlparse

import requests
from sqlalchemy.orm import Session

from app.models import ReleaseSource

logger = logging.getLogger(__name__)

_DATE_META_PATTERNS = [
    r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)["\']',
    r'<meta[^>]+name=["\']pubdate["\'][^>]+content=["\']([^"\']+)["\']',
    r'<meta[^>]+name=["\']publishdate["\'][^>]+content=["\']([^"\']+)["\']',
    r'<meta[^>]+name=["\']date["\'][^>]+content=["\']([^"\']+)["\']',
    r'<time[^>]+datetime=["\']([^"\']+)["\']',
]

_TITLE_PATTERNS = [
    r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
    r'<title>([^<]+)</title>',
]


def _normalize_utc_naive(value: datetime.datetime) -> datetime.datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(datetime.timezone.utc).replace(tzinfo=None)


def _parse_datetime(raw: str) -> datetime.datetime | None:
    value = (raw or "").strip()
    if not value:
        return None

    candidates = [value]
    if value.endswith("Z"):
        candidates.append(value[:-1] + "+00:00")

    for candidate in candidates:
        try:
            return _normalize_utc_naive(datetime.datetime.fromisoformat(candidate))
        except ValueError:
            pass

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime(value, fmt)
        except ValueError:
            continue

    return None


def _extract_hrefs(html: str) -> list[str]:
    hrefs = re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
    return [href.strip() for href in hrefs if href and href.strip()]


def _is_same_site(base_url: str, candidate_url: str) -> bool:
    base_host = (urlparse(base_url).netloc or "").lower().lstrip("www.")
    candidate_host = (urlparse(candidate_url).netloc or "").lower().lstrip("www.")
    if not base_host or not candidate_host:
        return False
    return candidate_host == base_host or candidate_host.endswith(f".{base_host}") or base_host.endswith(f".{candidate_host}")


def _is_valid_candidate_href(href: str) -> bool:
    token = (href or "").strip().lower()
    if not token:
        return False
    if token.startswith("#"):
        return False
    if token.startswith("javascript:") or token.startswith("mailto:") or token.startswith("tel:"):
        return False
    if "{{" in token or "}}" in token:
        return False
    return True


def _looks_like_release_link(url: str) -> bool:
    token = url.lower()
    if any(ext in token for ext in [".css", ".js", ".ico", ".png", ".jpg", ".jpeg", ".svg", ".pdf"]):
        return False

    # Prefer article-level detail pages instead of broad nav pages.
    has_release_section = any(
        word in token
        for word in ["/news-release", "/news-releases", "/press-release", "/press-releases", "/news/"]
    )
    has_detail_hint = bool(
        re.search(r"/(20\d{2}[/-]\d{1,2}[/-]\d{1,2}|\d{6,}|[a-z0-9-]+\.html?)", token)
    )
    if not has_release_section:
        return False

    # Skip common non-article investor navigation pages.
    if any(
        blocked in token
        for blocked in [
            "/overview",
            "/events",
            "/stock",
            "/financial",
            "/resources",
            "/governance",
            "/contact",
            "/alerts",
            "/faq",
            "/default.aspx",
        ]
    ):
        return False

    return has_detail_hint


def _fetch_html(url: str, timeout: int = 15) -> str | None:
    try:
        response = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        logger.warning("Release discovery fetch failed url=%s error=%s", url, exc)
        return None


def _extract_title(html: str, fallback: str) -> str:
    for pattern in _TITLE_PATTERNS:
        match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
        if match:
            value = re.sub(r"\s+", " ", match.group(1)).strip()
            if value:
                return value
    return fallback


def _extract_published_date(html: str) -> datetime.datetime | None:
    for pattern in _DATE_META_PATTERNS:
        match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
        if match:
            parsed = _parse_datetime(match.group(1))
            if parsed is not None:
                return parsed

    for pattern in [r"(20\d{2}-\d{2}-\d{2})", r"(20\d{2}/\d{2}/\d{2})"]:
        match = re.search(pattern, html)
        if match:
            parsed = _parse_datetime(match.group(1))
            if parsed is not None:
                return parsed
    return None


def discover_recent_releases(db: Session, now_utc: datetime.datetime | None = None) -> list[dict]:
    """Scan configured source pages and return releases published in last 24h."""
    now = now_utc or datetime.datetime.utcnow()
    cutoff = now - datetime.timedelta(hours=72)

    active_sources = (
        db.query(ReleaseSource)
        .filter(ReleaseSource.is_active == True)  # noqa: E712
        .order_by(ReleaseSource.id.asc())
        .all()
    )

    discovered: list[dict] = []
    seen_urls: set[str] = set()

    for source in active_sources:
        listing_html = _fetch_html(source.source_url, timeout=20)
        if not listing_html:
            continue

        source_domain = urlparse(source.source_url).netloc
        for href in _extract_hrefs(listing_html):
            if not _is_valid_candidate_href(href):
                continue

            absolute_url = urljoin(source.source_url, href)
            if absolute_url in seen_urls or not _looks_like_release_link(absolute_url):
                continue

            parsed = urlparse(absolute_url)
            if not parsed.scheme.startswith("http"):
                continue
            if not _is_same_site(source.source_url, absolute_url):
                continue

            seen_urls.add(absolute_url)
            article_html = _fetch_html(absolute_url)
            if not article_html:
                continue

            published_date = _extract_published_date(article_html)
            if published_date is None or published_date < cutoff or published_date > now:
                continue

            title = _extract_title(article_html, fallback=f"{source.company_name} release")
            discovered.append(
                {
                    "title": title,
                    "url": absolute_url,
                    "source_domain": parsed.netloc or source_domain,
                    "summary": f"Release discovered from {source.company_name}",
                    "full_text": "",
                    "score": 0,
                    "raw_score": 0,
                    "passed_relevance_filter": True,
                    "kept": True,
                    "rejection_reason": None,
                    "tags": "release",
                    "matched_query_id": None,
                    "published_date": published_date,
                    "article_type": "release",
                }
            )

    logger.info("Release discovery complete: discovered=%s", len(discovered))
    return discovered
