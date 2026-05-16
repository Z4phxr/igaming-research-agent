"""Search service: load active queries and call Serper API.

TODO: Implement full Serper pagination and robust retry/backoff.
"""

import logging
import os

import requests
from sqlalchemy.orm import Session

from app.models import Query

logger = logging.getLogger(__name__)


def _get_serper_api_key() -> str:
    """Return SERPER_API_KEY from environment or raise a clear error."""
    api_key = os.getenv("SERPER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "SERPER_API_KEY is missing. Set SERPER_API_KEY in your environment or .env file."
        )
    return api_key


def get_active_queries(db: Session) -> list[Query]:
    """Read and return active query records from SQLite."""
    return db.query(Query).filter(Query.is_active == True).all()  # noqa: E712


def execute_search(query: Query) -> list[dict]:
    """Execute one active query against Serper News and normalize response items.

    Returns list entries with: title, url, snippet, source, published_date.
    Logs warnings and returns an empty list if request/parsing fails.
    """
    api_key = _get_serper_api_key()
    search_term = (query.search_term or "").strip()
    if not search_term:
        logger.warning("Skipping query with empty search_term (id=%s)", getattr(query, "id", "unknown"))
        return []

    logger.info("Executing Serper query id=%s term=%s", getattr(query, "id", "unknown"), search_term)

    try:
        response = requests.post(
            "https://google.serper.dev/news",
            headers={
                "X-API-KEY": api_key,
                "Content-Type": "application/json",
            },
            json={
                "q": search_term,
                "num": 10,
                "tbs": "qdr:d",
            },
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning(
            "Serper request failed for query id=%s term=%s: %s",
            getattr(query, "id", "unknown"),
            search_term,
            exc,
        )
        return []

    try:
        payload = response.json()
    except ValueError as exc:
        logger.warning(
            "Serper response parsing failed for query id=%s term=%s: %s",
            getattr(query, "id", "unknown"),
            search_term,
            exc,
        )
        return []

    news_items = payload.get("news", []) if isinstance(payload, dict) else []
    if not isinstance(news_items, list):
        logger.warning(
            "Unexpected Serper response shape for query id=%s term=%s",
            getattr(query, "id", "unknown"),
            search_term,
        )
        return []

    normalized: list[dict] = []
    for item in news_items:
        if not isinstance(item, dict):
            continue
        url = (item.get("link") or item.get("url") or "").strip()
        if not url:
            continue
        normalized.append(
            {
                "title": item.get("title") or "Untitled",
                "url": url,
                "snippet": item.get("snippet") or "",
                "source": item.get("source") or "",
                "published_date": item.get("date") or item.get("published_date") or item.get("publishedAt"),
                "matched_query_id": getattr(query, "id", None),
                "matched_search_term": search_term,
            }
        )

    logger.info(
        "Serper query id=%s returned %s results",
        getattr(query, "id", "unknown"),
        len(normalized),
    )
    return normalized


def run_search_pipeline(db: Session) -> list[dict]:
    """Run active queries, merge results, and deduplicate by URL.

    Continues on single-query failures, but raises clearly when API key is missing.
    """
    _get_serper_api_key()

    queries = get_active_queries(db)
    all_results: list[dict] = []

    for query in queries:
        try:
            results = execute_search(query)
            logger.info(
                "Query id=%s term=%s produced %s results",
                getattr(query, "id", "unknown"),
                query.search_term,
                len(results),
            )
            all_results.extend(results)
        except Exception as exc:
            logger.warning(
                "Query id=%s term=%s failed and will be skipped: %s",
                getattr(query, "id", "unknown"),
                getattr(query, "search_term", "unknown"),
                exc,
            )

    seen_urls: set[str] = set()
    deduplicated: list[dict] = []
    for item in all_results:
        url = str(item.get("url", "")).strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        deduplicated.append(item)

    logger.info(
        "Search pipeline complete: raw_total=%s deduplicated_total=%s",
        len(all_results),
        len(deduplicated),
    )

    # TODO: Pass deduplicated output to scraper service for full-text extraction.
    return deduplicated


def search_with_serper(search_term: str) -> list[dict]:
    """Backward-compatible wrapper around execute_search for existing callers."""
    query = Query(search_term=search_term, stream_type="business", is_active=True)
    return execute_search(query)
