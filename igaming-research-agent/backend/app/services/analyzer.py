"""Analyzer service: send article text to LLM for relevance/scoring/summary.

TODO: Integrate Anthropic Claude client calls for both relevance and scoring.
"""

import logging
import os
import re
from typing import Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

_openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
if not _openai_api_key:
    raise RuntimeError("OPENAI_API_KEY is missing. Set OPENAI_API_KEY in your environment or .env file.")

client = OpenAI(api_key=_openai_api_key)

_MODEL = "gpt-4o-mini"

_RELEVANCE_SYSTEM_PROMPT = """
You are a strict content filter for a USA iGaming research agent.
Answer only YES or NO.
Answer YES only if the article is ALL of these:
- About the United States specifically (not Europe, Asia, or global)
- About at least one of: sports betting, iGaming, online casino,
  fantasy sports, prediction markets (Polymarket, Kalshi, PredictIt)
- News or analysis (not a betting guide, player tips, or sponsored content)
Answer NO for everything else.
"""

_SCORING_SYSTEM_PROMPT = """
You are a senior analyst for a USA iGaming investment research firm.
Analyze the article and respond in this EXACT format with no extra text:

SCORE: [number 1-10]
SUMMARY: [exactly 3 sentences summarizing the key business impact]
TAGS: [comma separated tags from: legislation, M&A, earnings,
       regulation, technology, prediction-markets, tribal-gaming,
       federal, licensing, executive-moves]

Scoring guide:
9-10: Major federal ruling, landmark legislation, billion-dollar M&A
7-8: State legislation passed, significant earnings, notable partnership
5-6: Regulatory meeting, minor licensing update, industry trend piece
1-4: Minor news, speculative, low business impact
"""


def _safe_article(article: dict) -> dict:
    """Normalize article dict so downstream prompt construction is robust."""
    return {
        "title": str(article.get("title", "")),
        "snippet": str(article.get("snippet", "")),
        "full_text": str(article.get("full_text", "")) if article.get("full_text") is not None else "",
        "url": str(article.get("url", "")),
        "source_domain": str(article.get("source_domain", "")),
    }


def is_relevant(article: dict) -> bool:
    """Run stage-one binary relevance check (YES/NO) for a scraped article."""
    item = _safe_article(article)
    user_message = f"Title: {item['title']}\n\nSnippet: {item['snippet']}"

    try:
        # Cost optimization: max_tokens=5 for a strict YES/NO answer.
        # Cost optimization: temperature=0 for deterministic outputs.
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _RELEVANCE_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=5,
            temperature=0,
        )
        content = (response.choices[0].message.content or "").strip()
        return "YES" in content.upper()
    except Exception as exc:
        logger.warning("Relevance check failed for url=%s error=%s", item.get("url", ""), exc)
        return False


def score_and_summarize(article: dict | str) -> Optional[dict]:
    """Run stage-two scoring and 3-sentence summarization for a relevant article.

    Accepts the primary dict payload, and also supports legacy raw-text input
    for backward compatibility with existing scheduler call paths.
    """
    if isinstance(article, str):
        item = {
            "title": "",
            "snippet": "",
            "full_text": article,
            "url": "",
            "source_domain": "",
        }
    else:
        item = _safe_article(article)

    content = item["full_text"].strip() or item["snippet"].strip()
    user_message = f"Title: {item['title']}\n\nContent: {content[:3000]}"

    try:
        # Cost optimization: content is truncated to 3000 chars before request.
        # Cost optimization: temperature=0 for deterministic outputs.
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _SCORING_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=200,
            temperature=0,
        )
    except Exception as exc:
        logger.warning("Scoring failed for url=%s error=%s", item.get("url", ""), exc)
        return None

    raw = (response.choices[0].message.content or "").strip()

    score_match = re.search(r"SCORE:\s*(\d{1,2})", raw, re.IGNORECASE)
    summary_match = re.search(r"SUMMARY:\s*(.*?)\n\s*TAGS:\s*", raw, re.IGNORECASE | re.DOTALL)
    tags_match = re.search(r"TAGS:\s*(.+)$", raw, re.IGNORECASE | re.DOTALL)

    if not score_match or not summary_match or not tags_match:
        logger.warning("Failed to parse scoring response for url=%s response=%s", item.get("url", ""), raw)
        return None

    try:
        score = int(score_match.group(1))
    except ValueError:
        logger.warning("Invalid score value for url=%s response=%s", item.get("url", ""), raw)
        return None

    summary = summary_match.group(1).strip()
    tags = tags_match.group(1).strip()

    base_article = (
        article
        if isinstance(article, dict)
        else {
            "title": item["title"],
            "snippet": item["snippet"],
            "full_text": item["full_text"],
            "url": item["url"],
            "source_domain": item["source_domain"],
        }
    )

    return {
        **base_article,
        "score": score,
        "summary": summary,
        "tags": tags,
    }


def run_analysis_pipeline(articles: list[dict]) -> list[dict]:
    """Run two-stage relevance and scoring pipeline over scraped articles."""
    if not articles:
        logger.info("Analysis pipeline received no articles; nothing to do")
        return []

    relevant_articles: list[dict] = []
    for article in articles:
        if is_relevant(article):
            relevant_articles.append(article)

    logger.info("Analysis stage 1 complete: relevant=%s total=%s", len(relevant_articles), len(articles))

    scored_results: list[dict] = []
    for article in relevant_articles:
        scored = score_and_summarize(article)
        if scored is not None:
            scored_results.append(scored)

    logger.info("Analysis stage 2 complete: scored_successfully=%s", len(scored_results))

    before_score_filter = len(scored_results)
    high_impact = [item for item in scored_results if int(item.get("score", 0)) >= 6]
    dropped_low_score = before_score_filter - len(high_impact)
    logger.info("Analysis score filter complete: dropped_low_score=%s", dropped_low_score)

    high_impact.sort(key=lambda x: int(x.get("score", 0)), reverse=True)
    final = high_impact[:10]

    if not final:
        logger.warning("Analysis pipeline produced no final articles")
        return []

    logger.info("Analysis pipeline complete: final_output=%s", len(final))

    # TODO: Pass analyzed results to report persistence service.
    return final


def is_relevant_article(text: str) -> bool:
    """Compatibility alias for legacy scheduler callers using raw article text."""
    return is_relevant(
        {
            "title": "",
            "snippet": text[:500],
            "full_text": text,
            "url": "",
            "source_domain": "",
        }
    )


def score_and_summarize_article(article: dict) -> Optional[dict]:
    """Compatibility alias for explicit article-based stage-two calls."""
    return score_and_summarize(article)
