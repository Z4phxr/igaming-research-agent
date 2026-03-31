"""Discover company release links from configured source pages."""

import datetime
import email.utils
import logging
import random
import re
import time
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse

import requests
from sqlalchemy.orm import Session

from app.config import settings
from app.models import ReleaseSource
from app.services.portal_scrapers import resolve_listing_parser

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
_SOURCE_LISTING_TIMEOUT_OVERRIDES_SECONDS = {
    "investors.wynnresorts.com": 90,
    "investors.pennentertainment.com": 90,
    "www.ballys.com": 60,
}
_SOURCE_TLS_INSECURE_HOSTS = {
    "newsroom.playags.com",
}
_SOURCE_LISTING_JINA_FALLBACK_HOSTS = {
    "www.catenamedia.com",
    "catenamedia.com",
    "www.draftkings.com",
    "draftkings.com",
    "news.bet365.com",
}


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


def _append_failed_source(
    failed_sources: list[dict] | None,
    source: ReleaseSource,
    reason: str,
    stage: str,
    status_code: int | None,
    checked_at: datetime.datetime,
) -> None:
    if failed_sources is None:
        return

    source_url = str(source.source_url or "").strip()
    if not source_url:
        return

    if any(str(item.get("source_url") or "").strip() == source_url for item in failed_sources):
        return

    failed_sources.append(
        {
            "company_name": source.company_name,
            "source_url": source_url,
            "reason": reason,
            "stage": stage,
            "http_status": status_code,
            "checked_at": checked_at,
        }
    )


def _increment_failure_reason(stats: dict, reason: str) -> None:
    failed_by_reason = stats["failed_by_reason"]
    failed_by_reason[reason] = int(failed_by_reason.get(reason, 0)) + 1


def _should_quarantine(error_kind: str) -> bool:
    return error_kind in {"timeout", "connection_error", "http_403", "http_429", "ssl_error"}


def _rate_limit_guard(
    domain: str,
    source: ReleaseSource,
    state: dict,
    now_utc: datetime.datetime,
) -> tuple[bool, str]:
    entry = state.setdefault(
        domain,
        {
            "window_start": now_utc,
            "count": 0,
            "last_request_monotonic": 0.0,
        },
    )

    if (now_utc - entry["window_start"]) >= datetime.timedelta(hours=1):
        entry["window_start"] = now_utc
        entry["count"] = 0

    max_per_hour = int(getattr(source, "max_requests_per_hour", settings.release_domain_default_hourly_limit) or 1)
    max_per_hour = max(1, max_per_hour)
    if entry["count"] >= max_per_hour:
        return False, "local_rate_limit"

    delay_seconds = int(getattr(source, "crawl_delay_seconds", settings.release_domain_default_crawl_delay_seconds) or 0)
    delay_seconds = max(0, delay_seconds)
    now_monotonic = time.perf_counter()
    elapsed = now_monotonic - float(entry["last_request_monotonic"])
    jitter = random.uniform(0.0, max(0.0, settings.release_request_jitter_seconds))
    required_wait = float(delay_seconds) + jitter
    if elapsed < required_wait:
        time.sleep(required_wait - elapsed)

    entry["count"] += 1
    entry["last_request_monotonic"] = time.perf_counter()
    return True, "ok"


def _mark_source_failure(source: ReleaseSource, reason: str, now_utc: datetime.datetime) -> None:
    current_failures = int(getattr(source, "consecutive_failures", 0) or 0) + 1
    source.consecutive_failures = current_failures
    source.last_failure_reason = reason
    source.health_score = max(0, int(getattr(source, "health_score", 100) or 100) - 8)

    threshold = max(1, settings.release_quarantine_failure_threshold)
    if current_failures >= threshold and _should_quarantine(reason):
        source.quarantine_until = now_utc + datetime.timedelta(hours=max(1, settings.release_quarantine_hours))


def _mark_source_success(source: ReleaseSource, now_utc: datetime.datetime) -> None:
    source.consecutive_failures = 0
    source.last_failure_reason = None
    source.last_success_at = now_utc
    source.quarantine_until = None
    source.health_score = min(100, int(getattr(source, "health_score", 100) or 100) + 2)


def _is_feed_source(source: ReleaseSource) -> bool:
    method = str(getattr(source, "preferred_method", "auto") or "auto").lower()
    if method == "feed":
        return True
    if method == "html":
        return False
    if not settings.release_enable_feed_first:
        return False
    token = (source.source_url or "").lower()
    return any(part in token for part in ["/feed", "rss", "atom", "xml"])


def _listing_timeout_for_source(source_url: str) -> int:
    """Return effective listing timeout with per-domain floor for slow portals."""
    base_timeout = max(1, int(settings.release_listing_fetch_timeout_seconds or 1))
    host = urlparse(source_url or "").netloc.lower()
    override_timeout = _SOURCE_LISTING_TIMEOUT_OVERRIDES_SECONDS.get(host)
    if override_timeout is None:
        return base_timeout
    return max(base_timeout, int(override_timeout))


def _listing_url_candidates(source_url: str) -> list[str]:
    """Return preferred listing URL candidates for sources with known mirrored IR paths."""
    parsed = urlparse(source_url or "")
    host = (parsed.netloc or "").lower()
    path = parsed.path or ""

    candidates: list[str] = [source_url]

    if host == "investors.wynnresorts.com":
        if "/press-releases" in path:
            candidates.append(source_url.replace("/press-releases", "/news-releases"))
        candidates.append(f"{parsed.scheme}://{parsed.netloc}/news-releases")
        candidates.append(f"{parsed.scheme}://{parsed.netloc}/news-releases/")

    # Keep order while deduplicating.
    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        token = (candidate or "").strip()
        if not token or token in seen:
            continue
        deduped.append(token)
        seen.add(token)
    return deduped


def _request_verify_for_url(url: str) -> bool:
    """Return TLS verification mode for a source URL."""
    host = (urlparse(url or "").netloc or "").lower()
    return host not in _SOURCE_TLS_INSECURE_HOSTS


def _should_try_jina_listing_fallback(url: str, stage: str, error_kind: str) -> bool:
    if error_kind != "http_403":
        return False
    if not str(stage or "").startswith("listing_fetch"):
        return False
    host = (urlparse(url or "").netloc or "").lower()
    return host in _SOURCE_LISTING_JINA_FALLBACK_HOSTS


def _fetch_html_via_jina(url: str, timeout: int, headers: dict[str, str]) -> tuple[str, int]:
    jina_url = f"https://r.jina.ai/{url}"
    response = requests.get(jina_url, timeout=timeout, headers=headers)
    response.raise_for_status()
    return response.text, int(response.status_code)


def _discover_from_feed_xml(
    source: ReleaseSource,
    xml_text: str,
    cutoff: datetime.datetime,
    now_utc: datetime.datetime,
) -> list[dict]:
    discovered: list[dict] = []
    source_domain = urlparse(source.source_url).netloc

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return discovered

    items = root.findall(".//item") + root.findall(".//{http://www.w3.org/2005/Atom}entry")
    for item in items:
        link_node = item.find("link") or item.find("{http://www.w3.org/2005/Atom}link")
        href = ""
        if link_node is not None:
            href = (link_node.attrib.get("href") or link_node.text or "").strip()
        if not href:
            continue

        title_node = item.find("title") or item.find("{http://www.w3.org/2005/Atom}title")
        title = (title_node.text or "").strip() if title_node is not None else ""
        date_node = (
            item.find("pubDate")
            or item.find("published")
            or item.find("updated")
            or item.find("{http://www.w3.org/2005/Atom}published")
            or item.find("{http://www.w3.org/2005/Atom}updated")
        )
        date_raw = (date_node.text or "").strip() if date_node is not None else ""
        published = _parse_datetime(date_raw)
        if published is None and date_raw:
            try:
                published = email.utils.parsedate_to_datetime(date_raw)
                if published is not None:
                    published = _normalize_utc_naive(published)
            except (TypeError, ValueError):
                published = None

        if published is None or published < cutoff or published > now_utc:
            continue

        discovered.append(
            {
                "title": title or f"{source.company_name} release",
                "url": href,
                "source_domain": source_domain,
                "summary": f"Release discovered from {source.company_name}",
                "full_text": "",
                "score": 0,
                "raw_score": 0,
                "passed_relevance_filter": True,
                "kept": True,
                "rejection_reason": None,
                "tags": "release",
                "matched_query_id": None,
                "published_date": published,
                "article_type": "release",
            }
        )

    return discovered


def _log_page_result(
    page_name: str,
    page_url: str,
    stage: str,
    result: str,
    scraped_relevant: int,
    reason: str,
    http_status: int | None,
    duration_ms: int,
    retries_used: int,
) -> None:
    logger.info(
        "page_result page_name=%s page_url=%s stage=%s result=%s scraped_relevant=%s reason=%s http_status=%s duration_ms=%s retries_used=%s",
        page_name,
        page_url,
        stage,
        result,
        scraped_relevant,
        reason,
        http_status,
        duration_ms,
        retries_used,
    )


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


def _extract_embedded_model_urls(listing_html: str, source_url: str) -> list[str]:
    html = listing_html or ""
    found: list[str] = []
    seen: set[str] = set()

    patterns = [
        r'data-api-url=["\']([^"\']*\.model\.json)["\']',
        r'data-news-feed-url=["\']([^"\']*\.model\.json)["\']',
    ]
    for pattern in patterns:
        for rel in re.findall(pattern, html, flags=re.IGNORECASE):
            absolute = urljoin(source_url, rel.strip())
            if absolute and absolute not in seen:
                seen.add(absolute)
                found.append(absolute)

    return found


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
    verify = _request_verify_for_url(url)

    attempt = 0
    started = time.perf_counter()
    last_error_kind = "request_error"
    last_error_message = "unknown"
    last_status_code: int | None = None

    while attempt <= retries:
        request_started = time.perf_counter()
        try:
            response = requests.get(url, timeout=timeout, headers=headers, verify=verify)
            response.raise_for_status()
            duration_ms = int((time.perf_counter() - started) * 1000)
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

            if _should_try_jina_listing_fallback(url=url, stage=stage, error_kind=last_error_kind):
                try:
                    jina_html, jina_status = _fetch_html_via_jina(url=url, timeout=timeout, headers=headers)
                    duration_ms = int((time.perf_counter() - started) * 1000)
                    return jina_html, {
                        "ok": True,
                        "error_kind": "success",
                        "status_code": jina_status,
                        "duration_ms": duration_ms,
                        "retries_used": attempt,
                    }
                except requests.RequestException as jina_exc:
                    logger.info(
                        "listing_jina_fallback_failed page_url=%s stage=%s primary_error=%s fallback_error=%s",
                        url,
                        stage,
                        last_error_message,
                        str(jina_exc),
                    )

            should_retry = attempt < retries and _is_retryable_error(last_error_kind, last_status_code)

            if should_retry:
                backoff_seconds = settings.release_fetch_backoff_seconds * (2**attempt)
                logger.info(
                    "page_retry page_name=%s page_url=%s stage=%s reason=%s http_status=%s attempt=%s attempt_duration_ms=%s backoff_seconds=%.2f",
                    source_name,
                    url,
                    stage,
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


def discover_recent_releases(
    db: Session,
    now_utc: datetime.datetime | None = None,
    window_hours: int | None = None,
    failed_sources: list[dict] | None = None,
) -> list[dict]:
    """Scan configured source pages and return releases within configured recent window."""
    now = now_utc or datetime.datetime.utcnow()
    effective_window_hours = int(window_hours or settings.release_recent_window_hours)
    effective_window_hours = max(1, effective_window_hours)
    cutoff = now - datetime.timedelta(hours=effective_window_hours)

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
    run_pages_total = 0
    run_pages_success = 0
    run_relevant_pages = 0
    domain_state: dict[str, dict] = {}

    for source in active_sources:
        source_stats = _new_source_stats(source)
        source_now = now_utc or datetime.datetime.utcnow()
        listing_timeout = _listing_timeout_for_source(source.source_url)

        quarantine_until = getattr(source, "quarantine_until", None)
        if quarantine_until is not None and quarantine_until > source_now:
            run_pages_total += 1
            run_sources_failed += 1
            source_stats["listing_failed"] = 1
            source_stats["listing_failure_reason"] = "quarantined"
            _increment_failure_reason(source_stats, "quarantined")
            _append_failed_source(
                failed_sources=failed_sources,
                source=source,
                reason="quarantined",
                stage="listing",
                status_code=None,
                checked_at=source_now,
            )
            _mark_source_failure(source, "quarantined", source_now)
            db.add(source)
            db.commit()
            _log_page_result(
                page_name=source.company_name,
                page_url=source.source_url,
                stage="listing",
                result="fail",
                scraped_relevant=0,
                reason="quarantined",
                http_status=None,
                duration_ms=0,
                retries_used=0,
            )
            _log_source_summary(source_stats)
            continue

        domain = urlparse(source.source_url).netloc.lower()
        allowed, guard_reason = _rate_limit_guard(domain, source, domain_state, source_now)
        if not allowed:
            run_pages_total += 1
            run_sources_failed += 1
            source_stats["listing_failed"] = 1
            source_stats["listing_failure_reason"] = guard_reason
            _increment_failure_reason(source_stats, guard_reason)
            _append_failed_source(
                failed_sources=failed_sources,
                source=source,
                reason=guard_reason,
                stage="listing",
                status_code=None,
                checked_at=source_now,
            )
            _mark_source_failure(source, guard_reason, source_now)
            db.add(source)
            db.commit()
            _log_page_result(
                page_name=source.company_name,
                page_url=source.source_url,
                stage="listing",
                result="fail",
                scraped_relevant=0,
                reason=guard_reason,
                http_status=None,
                duration_ms=0,
                retries_used=0,
            )
            _log_source_summary(source_stats)
            continue

        if _is_feed_source(source):
            run_pages_total += 1
            feed_text, feed_meta = _fetch_html(
                source.source_url,
                source_name=source.company_name,
                stage="feed_fetch",
                timeout=listing_timeout,
            )
            source.last_listing_checked_at = source_now
            if not feed_text:
                reason = str(feed_meta["error_kind"])
                _append_failed_source(
                    failed_sources=failed_sources,
                    source=source,
                    reason=reason,
                    stage="feed",
                    status_code=feed_meta.get("status_code"),
                    checked_at=source_now,
                )
                _mark_source_failure(source, reason, source_now)
                db.add(source)
                db.commit()

                source_stats["listing_failed"] = 1
                source_stats["listing_failure_reason"] = reason
                _increment_failure_reason(source_stats, reason)
                _log_page_result(
                    page_name=source.company_name,
                    page_url=source.source_url,
                    stage="feed",
                    result="fail",
                    scraped_relevant=0,
                    reason=reason,
                    http_status=feed_meta.get("status_code"),
                    duration_ms=int(feed_meta.get("duration_ms", 0)),
                    retries_used=int(feed_meta.get("retries_used", 0)),
                )
                run_sources_failed += 1
                if reason == "timeout":
                    run_timeouts += 1
                if reason in {"http_403", "http_429"}:
                    run_blocked += 1
                _log_source_summary(source_stats)
                continue

            feed_discovered = _discover_from_feed_xml(source, feed_text, cutoff, source_now)
            source_stats["listing_ok"] = 1
            source_stats["accepted"] = len(feed_discovered)
            run_pages_success += 1
            if feed_discovered:
                run_relevant_pages += len(feed_discovered)
                discovered.extend(feed_discovered)
                _log_page_result(
                    page_name=source.company_name,
                    page_url=source.source_url,
                    stage="feed",
                    result="success",
                    scraped_relevant=len(feed_discovered),
                    reason="-",
                    http_status=feed_meta.get("status_code"),
                    duration_ms=int(feed_meta.get("duration_ms", 0)),
                    retries_used=int(feed_meta.get("retries_used", 0)),
                )
            else:
                _log_page_result(
                    page_name=source.company_name,
                    page_url=source.source_url,
                    stage="feed",
                    result="success",
                    scraped_relevant=0,
                    reason="no_recent_feed_items",
                    http_status=feed_meta.get("status_code"),
                    duration_ms=int(feed_meta.get("duration_ms", 0)),
                    retries_used=int(feed_meta.get("retries_used", 0)),
                )

            _mark_source_success(source, source_now)
            db.add(source)
            db.commit()
            run_sources_ok += 1
            _log_source_summary(source_stats)
            continue

        run_pages_total += 1
        listing_html = None
        listing_meta: dict = {
            "ok": False,
            "error_kind": "request_error",
            "status_code": None,
            "duration_ms": 0,
            "retries_used": 0,
        }
        listing_url_used = source.source_url
        for idx, listing_candidate_url in enumerate(_listing_url_candidates(source.source_url)):
            listing_html, listing_meta = _fetch_html(
                listing_candidate_url,
                source_name=source.company_name,
                stage="listing_fetch" if idx == 0 else "listing_fetch_fallback",
                timeout=listing_timeout,
            )
            if listing_html:
                listing_url_used = listing_candidate_url
                break

        source.last_listing_checked_at = source_now
        source.last_listing_etag = None
        source.last_listing_modified = None
        if not listing_html:
            source_stats["listing_failed"] = 1
            source_stats["listing_failure_reason"] = listing_meta["error_kind"]
            _increment_failure_reason(source_stats, str(listing_meta["error_kind"]))
            _append_failed_source(
                failed_sources=failed_sources,
                source=source,
                reason=str(listing_meta["error_kind"]),
                stage="listing",
                status_code=listing_meta.get("status_code"),
                checked_at=source_now,
            )
            _mark_source_failure(source, str(listing_meta["error_kind"]), source_now)
            db.add(source)
            db.commit()
            _log_page_result(
                page_name=source.company_name,
                page_url=source.source_url,
                stage="listing",
                result="fail",
                scraped_relevant=0,
                reason=str(listing_meta["error_kind"]),
                http_status=listing_meta.get("status_code"),
                duration_ms=int(listing_meta.get("duration_ms", 0)),
                retries_used=int(listing_meta.get("retries_used", 0)),
            )
            if listing_meta["error_kind"] == "timeout":
                run_timeouts += 1
            if listing_meta["error_kind"] in {"http_403", "http_429"}:
                run_blocked += 1
            run_sources_failed += 1
            _log_source_summary(source_stats)
            continue
        source_stats["listing_ok"] = 1
        run_pages_success += 1

        # Dynamic AEM list/news-feed components often publish content via model.json endpoints.
        for aux_url in _extract_embedded_model_urls(listing_html, listing_url_used)[:2]:
            aux_html, _ = _fetch_html(
                aux_url,
                source_name=source.company_name,
                stage="listing_aux_fetch",
                timeout=listing_timeout,
                max_retries=1,
            )
            if aux_html:
                listing_html = f"{listing_html}\n{aux_html}"

        source_domain = urlparse(source.source_url).netloc
        source_fetch_budget = max(1, settings.release_max_fetches_per_source)
        source_links_limit = max(1, settings.release_max_links_per_source)
        listing_empty_reason = "no_candidate_links"
        listing_candidates: list[str] = []
        listing_candidate_titles: dict[str, str] = {}
        listing_candidate_dates: dict[str, datetime.datetime] = {}
        parser = resolve_listing_parser(source.source_url, source.company_name)
        if parser is not None:
            parse_result = parser.parse_listing(
                listing_html,
                source.source_url,
                source.company_name,
                cutoff=cutoff,
                now_utc=now,
            )
            listing_candidates = parse_result.candidate_urls
            listing_candidate_titles = parse_result.candidate_titles
            listing_candidate_dates = parse_result.candidate_published_dates
            if parse_result.empty_reason:
                listing_empty_reason = parse_result.empty_reason
        else:
            listing_candidates = _extract_hrefs(listing_html)

        if not listing_candidates and listing_empty_reason in {"bot_protection_blocked", "tls_certificate_error"}:
            source_stats["listing_failed"] = 1
            source_stats["listing_failure_reason"] = listing_empty_reason
            _increment_failure_reason(source_stats, listing_empty_reason)
            _append_failed_source(
                failed_sources=failed_sources,
                source=source,
                reason=listing_empty_reason,
                stage="listing_parse",
                status_code=listing_meta.get("status_code"),
                checked_at=source_now,
            )
            _mark_source_failure(source, listing_empty_reason, source_now)
            db.add(source)
            db.commit()
            _log_page_result(
                page_name=source.company_name,
                page_url=source.source_url,
                stage="listing",
                result="fail",
                scraped_relevant=0,
                reason=listing_empty_reason,
                http_status=listing_meta.get("status_code"),
                duration_ms=int(listing_meta.get("duration_ms", 0)),
                retries_used=int(listing_meta.get("retries_used", 0)),
            )
            run_sources_failed += 1
            _log_source_summary(source_stats)
            continue

        for href in listing_candidates:
            if not _is_valid_candidate_href(href):
                continue

            absolute_url = urljoin(source.source_url, href)
            if absolute_url in seen_urls:
                continue
            if parser is None and not _looks_like_release_link(absolute_url):
                continue

            parsed = urlparse(absolute_url)
            if not parsed.scheme.startswith("http"):
                continue
            if not _is_same_site(source.source_url, absolute_url):
                continue

            if source_stats["candidates_total"] >= source_links_limit:
                break

            seen_urls.add(absolute_url)
            source_stats["candidates_total"] += 1
            run_pages_total += 1

            published_date = listing_candidate_dates.get(absolute_url)
            article_title_hint = listing_candidate_titles.get(absolute_url)
            article_html = ""
            article_meta: dict[str, int | str | bool | None] = {
                "status_code": None,
                "duration_ms": 0,
                "retries_used": 0,
            }

            if published_date is None:
                if source_stats["attempted_article_fetches"] >= source_fetch_budget:
                    break
                source_stats["attempted_article_fetches"] += 1

                domain = urlparse(absolute_url).netloc.lower()
                allowed, guard_reason = _rate_limit_guard(domain, source, domain_state, now)
                if not allowed:
                    source_stats["article_fetch_failed"] += 1
                    _increment_failure_reason(source_stats, guard_reason)
                    _log_page_result(
                        page_name=source.company_name,
                        page_url=absolute_url,
                        stage="article",
                        result="fail",
                        scraped_relevant=0,
                        reason=guard_reason,
                        http_status=None,
                        duration_ms=0,
                        retries_used=0,
                    )
                    continue

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
                    _log_page_result(
                        page_name=source.company_name,
                        page_url=absolute_url,
                        stage="article",
                        result="fail",
                        scraped_relevant=0,
                        reason=reason,
                        http_status=article_meta.get("status_code"),
                        duration_ms=int(article_meta.get("duration_ms", 0)),
                        retries_used=int(article_meta.get("retries_used", 0)),
                    )
                    if reason == "timeout":
                        run_timeouts += 1
                    if reason in {"http_403", "http_429"}:
                        run_blocked += 1
                    continue
                source_stats["article_fetch_ok"] += 1

                published_date = _extract_published_date(article_html)
                if parser is not None:
                    published_date = parser.extract_article_published_date(article_html) or published_date

            run_pages_success += 1
            if published_date is None:
                source_stats["rejected_missing_date"] += 1
                _log_page_result(
                    page_name=source.company_name,
                    page_url=absolute_url,
                    stage="article",
                    result="success",
                    scraped_relevant=0,
                    reason="missing_published_date",
                    http_status=article_meta.get("status_code"),
                    duration_ms=int(article_meta.get("duration_ms", 0)),
                    retries_used=int(article_meta.get("retries_used", 0)),
                )
                continue

            if published_date < cutoff or published_date > now:
                source_stats["rejected_stale_or_future"] += 1
                _log_page_result(
                    page_name=source.company_name,
                    page_url=absolute_url,
                    stage="article",
                    result="success",
                    scraped_relevant=0,
                    reason="outside_time_window",
                    http_status=article_meta.get("status_code"),
                    duration_ms=int(article_meta.get("duration_ms", 0)),
                    retries_used=int(article_meta.get("retries_used", 0)),
                )
                if (
                    parser is not None
                    and published_date < cutoff
                    and parser.is_likely_descending_chronological()
                ):
                    # Newest->oldest listings allow stopping after first stale hit.
                    break
                continue

            if article_html:
                title = _extract_title(article_html, fallback=f"{source.company_name} release")
            else:
                title = article_title_hint or f"{source.company_name} release"
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
            run_relevant_pages += 1
            _log_page_result(
                page_name=source.company_name,
                page_url=absolute_url,
                stage="article",
                result="success",
                scraped_relevant=1,
                reason="-",
                http_status=article_meta.get("status_code"),
                duration_ms=int(article_meta.get("duration_ms", 0)),
                retries_used=int(article_meta.get("retries_used", 0)),
            )

        if source_stats["listing_ok"] == 1 and source_stats["candidates_total"] == 0:
            _log_page_result(
                page_name=source.company_name,
                page_url=source.source_url,
                stage="listing",
                result="success",
                scraped_relevant=0,
                reason=listing_empty_reason,
                http_status=listing_meta.get("status_code"),
                duration_ms=int(listing_meta.get("duration_ms", 0)),
                retries_used=int(listing_meta.get("retries_used", 0)),
            )
        elif source_stats["listing_ok"] == 1:
            _log_page_result(
                page_name=source.company_name,
                page_url=source.source_url,
                stage="listing",
                result="success",
                scraped_relevant=source_stats["accepted"],
                reason="-",
                http_status=listing_meta.get("status_code"),
                duration_ms=int(listing_meta.get("duration_ms", 0)),
                retries_used=int(listing_meta.get("retries_used", 0)),
            )

        run_sources_ok += 1
        if source_stats["listing_failed"] > 0:
            _mark_source_failure(source, str(source_stats["listing_failure_reason"]), source_now)
        else:
            _mark_source_success(source, source_now)
        db.add(source)
        db.commit()
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
    logger.info(
        "pages_summary success_pages=%s/%s successful_releases=%s/%s",
        run_pages_success,
        run_pages_total,
        run_relevant_pages,
        run_pages_total,
    )
    return discovered
