"""Discover company release links from configured source pages."""

import datetime
import logging
import re
import time
from urllib.parse import urljoin, urlparse

import requests
from sqlalchemy.orm import Session

from app.config import settings
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

_TRANSIENT_HTTP_STATUS = {429, 500, 502, 503, 504}


def _new_source_stats(source: ReleaseSource) -> dict:
    return {
        "source_id": source.id,
        "company_name": source.company_name,
        "listing_ok": 0,
        "listing_failed": 0,
        "listing_failure_reason": "",
        "candidates_total": 0,
        "attempted_article_fetches": 0,
        "article_fetch_ok": 0,
        "article_fetch_failed": 0,
        "accepted": 0,
        "rejected_missing_date": 0,
        "rejected_stale_or_future": 0,
        "failed_by_reason": {},
        "started_at": time.perf_counter(),
    }


def _increment_failure_reason(stats: dict, reason: str) -> None:
    failed_by_reason = stats["failed_by_reason"]
    failed_by_reason[reason] = int(failed_by_reason.get(reason, 0)) + 1


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


def _classify_request_error(exc: requests.RequestException) -> tuple[str, int | None]:
    if isinstance(exc, requests.exceptions.Timeout):
        return "timeout", None
    if isinstance(exc, requests.exceptions.SSLError):
        return "ssl_error", None
    if isinstance(exc, requests.exceptions.ConnectionError):
        return "connection_error", None
    if isinstance(exc, requests.exceptions.HTTPError):
        status = exc.response.status_code if exc.response is not None else None
        if status == 403:
            return "http_403", status
        if status == 404:
            return "http_404", status
        if status == 429:
            return "http_429", status
        if status is not None and status >= 500:
            return f"http_{status}", status
        if status is not None:
            return f"http_{status}", status
    return "request_error", None


def _is_retryable_error(error_kind: str, status_code: int | None) -> bool:
    if error_kind in {"timeout", "connection_error"}:
        return True
    if status_code is not None and status_code in _TRANSIENT_HTTP_STATUS:
        return True
    return False


def _fetch_html(
    url: str,
    source_name: str,
    stage: str,
    timeout: int,
    max_retries: int | None = None,
) -> tuple[str | None, dict]:
    retries = settings.release_fetch_max_retries if max_retries is None else max_retries
    retries = max(0, retries)

    headers = {"User-Agent": settings.release_fetch_user_agent}

    attempt = 0
    started = time.perf_counter()
    last_error_kind = "request_error"
    last_error_message = "unknown"
    last_status_code: int | None = None

    while attempt <= retries:
        request_started = time.perf_counter()
        try:
            response = requests.get(url, timeout=timeout, headers=headers)
            response.raise_for_status()
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.info(
                "release_fetch stage=%s status=success source=%s url=%s http_status=%s duration_ms=%s retries_used=%s bytes=%s",
                stage,
                source_name,
                url,
                response.status_code,
                duration_ms,
                attempt,
                len(response.text or ""),
            )
            return response.text, {
                "ok": True,
                "error_kind": "success",
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "retries_used": attempt,
            }
        except requests.RequestException as exc:
            last_error_kind, last_status_code = _classify_request_error(exc)
            last_error_message = str(exc)
            attempt_duration_ms = int((time.perf_counter() - request_started) * 1000)
            should_retry = attempt < retries and _is_retryable_error(last_error_kind, last_status_code)

            if should_retry:
                backoff_seconds = settings.release_fetch_backoff_seconds * (2**attempt)
                logger.info(
                    "release_fetch stage=%s status=retry source=%s url=%s error_kind=%s http_status=%s attempt=%s attempt_duration_ms=%s backoff_seconds=%.2f",
                    stage,
                    source_name,
                    url,
                    last_error_kind,
                    last_status_code,
                    attempt + 1,
                    attempt_duration_ms,
                    backoff_seconds,
                )
                time.sleep(max(0.0, backoff_seconds))
                attempt += 1
                continue
            break

    duration_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "release_fetch stage=%s status=failed source=%s url=%s error_kind=%s http_status=%s duration_ms=%s retries_used=%s error=%s",
        stage,
        source_name,
        url,
        last_error_kind,
        last_status_code,
        duration_ms,
        attempt,
        last_error_message,
    )
    return None, {
        "ok": False,
        "error_kind": last_error_kind,
        "status_code": last_status_code,
        "duration_ms": duration_ms,
        "retries_used": attempt,
    }


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


def _log_source_summary(stats: dict) -> None:
    elapsed_ms = int((time.perf_counter() - stats["started_at"]) * 1000)
    logger.info(
        "release_source_summary source_id=%s source=%s listing_ok=%s listing_failed=%s listing_failure_reason=%s candidates=%s article_fetch_attempted=%s article_fetch_ok=%s article_fetch_failed=%s accepted=%s rejected_missing_date=%s rejected_stale_or_future=%s failed_by_reason=%s elapsed_ms=%s",
        stats["source_id"],
        stats["company_name"],
        stats["listing_ok"],
        stats["listing_failed"],
        stats["listing_failure_reason"],
        stats["candidates_total"],
        stats["attempted_article_fetches"],
        stats["article_fetch_ok"],
        stats["article_fetch_failed"],
        stats["accepted"],
        stats["rejected_missing_date"],
        stats["rejected_stale_or_future"],
        stats["failed_by_reason"],
        elapsed_ms,
    )


def discover_recent_releases(db: Session, now_utc: datetime.datetime | None = None) -> list[dict]:
    """Scan configured source pages and return releases within configured recent window."""
    now = now_utc or datetime.datetime.utcnow()
    cutoff = now - datetime.timedelta(hours=settings.release_recent_window_hours)

    active_sources = (
        db.query(ReleaseSource)
        .filter(ReleaseSource.is_active == True)  # noqa: E712
        .order_by(ReleaseSource.id.asc())
        .all()
    )

    discovered: list[dict] = []
    seen_urls: set[str] = set()
    run_sources_failed = 0
    run_sources_ok = 0
    run_timeouts = 0
    run_blocked = 0

    for source in active_sources:
        source_stats = _new_source_stats(source)
        listing_html, listing_meta = _fetch_html(
            source.source_url,
            source_name=source.company_name,
            stage="listing_fetch",
            timeout=settings.release_listing_fetch_timeout_seconds,
        )
        if not listing_html:
            source_stats["listing_failed"] = 1
            source_stats["listing_failure_reason"] = listing_meta["error_kind"]
            _increment_failure_reason(source_stats, str(listing_meta["error_kind"]))
            if listing_meta["error_kind"] == "timeout":
                run_timeouts += 1
            if listing_meta["error_kind"] in {"http_403", "http_429"}:
                run_blocked += 1
            run_sources_failed += 1
            _log_source_summary(source_stats)
            continue
        source_stats["listing_ok"] = 1

        source_domain = urlparse(source.source_url).netloc
        source_fetch_budget = max(1, settings.release_max_fetches_per_source)
        source_links_limit = max(1, settings.release_max_links_per_source)
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

            if source_stats["candidates_total"] >= source_links_limit:
                break
            if source_stats["attempted_article_fetches"] >= source_fetch_budget:
                break

            seen_urls.add(absolute_url)
            source_stats["candidates_total"] += 1
            source_stats["attempted_article_fetches"] += 1
            article_html, article_meta = _fetch_html(
                absolute_url,
                source_name=source.company_name,
                stage="article_fetch",
                timeout=settings.release_fetch_timeout_seconds,
            )
            if not article_html:
                source_stats["article_fetch_failed"] += 1
                reason = str(article_meta["error_kind"])
                _increment_failure_reason(source_stats, reason)
                if reason == "timeout":
                    run_timeouts += 1
                if reason in {"http_403", "http_429"}:
                    run_blocked += 1
                continue
            source_stats["article_fetch_ok"] += 1

            published_date = _extract_published_date(article_html)
            if published_date is None:
                source_stats["rejected_missing_date"] += 1
                logger.info(
                    "release_extract status=rejected reason=missing_published_date source=%s url=%s",
                    source.company_name,
                    absolute_url,
                )
                continue

            if published_date < cutoff or published_date > now:
                source_stats["rejected_stale_or_future"] += 1
                logger.info(
                    "release_extract status=rejected reason=outside_time_window source=%s url=%s published_date=%s cutoff=%s now=%s",
                    source.company_name,
                    absolute_url,
                    published_date.isoformat(),
                    cutoff.isoformat(),
                    now.isoformat(),
                )
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
            source_stats["accepted"] += 1
            logger.info(
                "release_extract status=accepted source=%s url=%s published_date=%s title=%s",
                source.company_name,
                absolute_url,
                published_date.isoformat(),
                title,
            )

        run_sources_ok += 1
        _log_source_summary(source_stats)

    logger.info(
        "release_discovery_summary sources_total=%s sources_ok=%s sources_failed=%s discovered=%s timeouts=%s blocked=%s",
        len(active_sources),
        run_sources_ok,
        run_sources_failed,
        len(discovered),
        run_timeouts,
        run_blocked,
    )
    return discovered
