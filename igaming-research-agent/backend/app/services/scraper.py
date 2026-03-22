"""Scraper service: fetch article full text from URLs.

TODO: Integrate trafilatura extraction with timeout and fallback parser.
"""

import logging
from typing import Optional
from urllib.parse import urlparse

import requests

try:
    import trafilatura
except Exception:  # pragma: no cover - environment dependent
    trafilatura = None

logger = logging.getLogger(__name__)


def fetch_article_text(url: str) -> Optional[dict]:
    """Fetch and extract article text from a URL.

    Returns a dict with `url`, `full_text`, and `source_domain` on success.
    Returns None when fetching or extraction fails.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.Timeout as exc:
        logger.warning("Failed scraping url=%s error_type=Timeout error=%s", url, exc)
        return None
    except requests.ConnectionError as exc:
        logger.warning("Failed scraping url=%s error_type=ConnectionError error=%s", url, exc)
        return None
    except requests.HTTPError as exc:
        logger.warning("Failed scraping url=%s error_type=HTTPError error=%s", url, exc)
        return None
    except requests.RequestException as exc:
        logger.warning("Failed scraping url=%s error_type=RequestException error=%s", url, exc)
        return None
    except Exception as exc:
        logger.warning("Failed scraping url=%s error_type=Exception error=%s", url, exc)
        return None

    if trafilatura is None:
        logger.warning(
            "Failed extracting url=%s error_type=MissingDependency error=trafilatura is not installed",
            url,
        )
        return None

    try:
        full_text = trafilatura.extract(response.text, include_comments=False)
    except Exception as exc:
        logger.warning("Failed extracting url=%s error_type=TrafilaturaException error=%s", url, exc)
        return None

    if full_text is None:
        logger.warning("Failed extracting url=%s error_type=UnreadableContent error=trafilatura returned None", url)
        return None

    if not full_text.strip():
        logger.warning("Failed extracting url=%s error_type=EmptyContent error=extraction returned empty string", url)
        return None

    return {
        "url": url,
        "full_text": full_text,
        "source_domain": extract_source_domain(url),
    }


def extract_source_domain(url: str) -> str:
    """Extract and return the URL netloc/source domain."""
    parsed = urlparse(url)
    return parsed.netloc or url


def scrape_articles(articles: list[dict]) -> list[dict]:
    """Scrape full text for each search result article and return successful ones.

    Keeps all original article fields and appends `full_text` and `source_domain`.
    """
    if not articles:
        logger.info("Scrape pipeline received no articles; nothing to do")
        return []

    attempted = len(articles)
    succeeded = 0
    failed = 0
    results: list[dict] = []

    for article in articles:
        url = str(article.get("url", "")).strip()
        if not url:
            failed += 1
            logger.warning("Skipping article with missing URL: article=%s", article)
            continue

        scraped = fetch_article_text(url)
        if scraped is None:
            failed += 1
            continue

        merged = {
            **article,
            "full_text": scraped["full_text"],
            "source_domain": scraped["source_domain"],
        }
        results.append(merged)
        succeeded += 1

    logger.info(
        "Scrape pipeline complete: attempted=%s succeeded=%s failed=%s",
        attempted,
        succeeded,
        failed,
    )

    # TODO: Pass scraped articles to analyzer service for relevance and scoring.
    return results


def fetch_article_content(url: str) -> Optional[str]:
    """Compatibility helper: return only text for older call sites."""
    scraped = fetch_article_text(url)
    if not scraped:
        return None
    return str(scraped.get("full_text", "")).strip() or None
