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
    primary_error: str | None = None

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        if trafilatura is None:
            primary_error = "trafilatura is not installed"
        else:
            full_text = trafilatura.extract(response.text, include_comments=False)
            if full_text is None:
                primary_error = "trafilatura returned None"
            elif not full_text.strip():
                primary_error = "extraction returned empty string"
            else:
                return {
                    "url": url,
                    "full_text": full_text,
                    "source_domain": extract_source_domain(url),
                }
    except requests.Timeout as exc:
        primary_error = f"Timeout: {exc}"
    except requests.ConnectionError as exc:
        primary_error = f"ConnectionError: {exc}"
    except requests.HTTPError as exc:
        primary_error = f"HTTPError: {exc}"
    except requests.RequestException as exc:
        primary_error = f"RequestException: {exc}"
    except Exception as exc:
        primary_error = f"Exception: {exc}"

    logger.info("Using Jina fallback for %s", url)
    try:
        jina_url = f"https://r.jina.ai/{url}"
        response = requests.get(jina_url, timeout=15)
        response.raise_for_status()
        extracted_text = response.text
        if extracted_text and extracted_text.strip():
            return {
                "url": url,
                "full_text": extracted_text.strip(),
                "source_domain": extract_source_domain(url),
            }
    except Exception as exc:
        logger.warning(
            "Failed scraping url=%s primary_error=%s jina_error=%s",
            url,
            primary_error or "unknown primary error",
            exc,
        )
        return None

    logger.warning(
        "Failed scraping url=%s primary_error=%s jina_error=empty response",
        url,
        primary_error or "unknown primary error",
    )
    return None


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
