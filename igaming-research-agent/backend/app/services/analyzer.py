"""Analyzer service: send article text to LLM for relevance/scoring/summary.

TODO: Integrate Anthropic Claude client calls for both relevance and scoring.
"""

import logging
import os
import re
from typing import Optional

from anthropic import Anthropic

logger = logging.getLogger(__name__)

_anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
if not _anthropic_api_key:
    raise RuntimeError("ANTHROPIC_API_KEY is missing.")

anthropic_client = Anthropic(api_key=_anthropic_api_key)

# Cost optimization: Haiku used for simple classification
# and structured output tasks. Sonnet reserved for
# narrative generation in report_generator.py only.
_MODEL = os.getenv("ANTHROPIC_ANALYZER_MODEL", "claude-3-5-haiku-latest").strip() or "claude-3-5-haiku-latest"

_RELEVANCE_SYSTEM_PROMPT = """
You are a strict content filter for a USA iGaming research agent.
Answer only YES or NO.

Answer YES only if ALL of these are true:
- About the United States specifically (not Europe, Asia, or global/international)
- About legislation, regulation, M&A, earnings, licensing, executive moves or product updates
- Related to: sports betting, iGaming, online casino, fantasy sports, 
  prediction markets (Polymarket, Kalshi, PredictIt, etc.), VGTs, tribal gaming
- Contains at least one of: specific bill numbers (SB/HB/AB), Gaming Commission, 
  regulator names, company names (DraftKings, FanDuel, BetMGM, Penn, Caesars), 
  or federal agencies (CFTC, DOJ, SEC)

Answer NO if:
- Betting tips, odds, player guides, how-to content, sponsored reviews
- Traffic, weather, crime unrelated to gaming business
- Generic "gambling addiction" PSAs without policy angle
- International news (UK, Europe, Asia) unless it directly impacts USA companies
"""

_SCORING_SYSTEM_PROMPT = """
You are a senior analyst for a USA iGaming investment research firm.
Analyze the article and respond in this EXACT format with no extra text:

SCORE: [number 1-10]
SUMMARY: [exactly 3 sentences summarizing the key business impact]
TAGS: [comma separated tags from: legislation, M&A, earnings,
       regulation, technology, prediction-markets, tribal-gaming,
       federal, licensing, executive-moves]

Scoring guide (use USA-specific context):

10: Supreme Court ruling, federal law change (Wire Act, IGRA), 
    billion+ M&A (e.g., Flutter acquires major US operator)

9: CFTC/DOJ major decision on prediction markets, 
   state legislature PASSES major bill (not just introduced),
   DraftKings/FanDuel Q1 earnings beat with 50%+ growth

8: State Gaming Commission APPROVES new operator license,
   significant partnership (e.g., ESPN + Penn),
   tribal gaming compact signed by governor

7: State bill PASSES committee (not just introduced),
   operator launches in new state,
   Gaming Commission publishes revenue report showing trends

6: State legislator INTRODUCES bill (SB/HB with sponsor name),
   regulatory meeting agenda published,
   minor licensing update

5: Industry trend analysis citing specific data,
   op-ed by industry executive with new data

3-4: Speculative "X state could legalize next year" without bill,
     generic conference announcement,
     international news tangentially mentioning USA

1-2: Betting tips, player guides, odds, promotional content,
     traffic/weather/crime unless directly tied to gaming business impact

CRITICAL: If article mentions bill number (SB/HB/AB) + committee/vote, minimum score is 6.
If federal agency (CFTC/DOJ/SEC) takes action, minimum score is 8.
"""

_PRIORITY_KEYWORDS = [
    "sb ",
    "hb ",
    "ab ",
    "bill",
    "legislation",
    "gaming commission",
    "cftc",
    "doj",
    "sec",
    "vote",
    "approved",
    "signed",
    "ruling",
    "passed",
    "draftkings",
    "fanduel",
    "betmgm",
    "penn",
    "caesars",
    "revenue",
    "earnings",
    "m&a",
    "merger",
    "acquisition",
]


def _extract_key_content(article: dict, max_chars: int = 3000) -> str:
    """Build a context-rich article payload without blind truncation.

    CHANGE 1: Prioritize regulation/financial/company paragraphs first,
    then append remaining context while respecting max_chars.
    """
    item = _safe_article(article)
    title_line = f"Title: {item['title'].strip()}" if item["title"].strip() else ""
    full_text = item["full_text"].strip()
    snippet_line = f"Snippet: {item['snippet'].strip()}" if item["snippet"].strip() else ""

    if not full_text:
        fallback = "\n\n".join([part for part in [title_line, snippet_line] if part]).strip()
        return fallback[:max_chars] if fallback else ""

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", full_text) if p.strip()]
    if not paragraphs:
        paragraphs = [full_text]

    keyword_hits = lambda text: any(keyword in text.lower() for keyword in _PRIORITY_KEYWORDS)
    priority_paragraphs = [p for p in paragraphs if keyword_hits(p)]
    remaining_paragraphs = [p for p in paragraphs if p not in priority_paragraphs]

    content_parts: list[str] = []
    if title_line:
        content_parts.append(title_line)

    selected_priority = priority_paragraphs[:5]
    selected_paragraphs = selected_priority + remaining_paragraphs

    current = "\n\n".join(content_parts)
    for paragraph in selected_paragraphs:
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
        else:
            break

    if not current and paragraphs:
        return paragraphs[0][:max_chars]
    return current[:max_chars]


def _validate_scoring_output(score: int, tags: str, summary: str, article: dict) -> bool:
    """Validate scoring output consistency before persistence.

    CHANGE 2: Filter inconsistent LLM outputs to improve training data quality.
    """
    item = _safe_article(article)
    tags_lower = [tag.strip().lower() for tag in tags.split(",") if tag.strip()]

    if score >= 8:
        required = {"federal", "legislation", "m&a", "earnings"}
        if not any(tag in required for tag in tags_lower):
            logger.warning(
                "Scoring validation failed url=%s reason=high_score_missing_required_tags score=%s tags=%s",
                item.get("url", ""),
                score,
                tags,
            )
            return False

    if "federal" in tags_lower and score < 7:
        logger.warning(
            "Scoring validation failed url=%s reason=federal_tag_requires_min_score score=%s tags=%s",
            item.get("url", ""),
            score,
            tags,
        )
        return False

    if len(summary.strip()) < 100:
        logger.warning(
            "Scoring validation failed url=%s reason=summary_too_short summary_length=%s",
            item.get("url", ""),
            len(summary.strip()),
        )
        return False

    return True


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
        # CHANGE 3: migrated model calls from OpenAI chat completions to Anthropic messages API.
        response = anthropic_client.messages.create(
            model=_MODEL,
            max_tokens=10,
            temperature=0,
            system=_RELEVANCE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        content = response.content[0].text.strip() if response.content else ""
        return "YES" in content.upper()
    except Exception as exc:
        logger.warning(
            "Relevance check failed for url=%s model=%s error=%s",
            item.get("url", ""),
            _MODEL,
            exc,
        )
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

    # CHANGE 1: Replace blind content truncation with keyword-prioritized chunk selection.
    content = _extract_key_content(item, max_chars=3000)
    user_message = f"Content: {content}"

    try:
        # Cost optimization: content is truncated to 3000 chars before request.
        # Cost optimization: temperature=0 for deterministic outputs.
        # CHANGE 3: migrated model calls from OpenAI chat completions to Anthropic messages API.
        response = anthropic_client.messages.create(
            model=_MODEL,
            max_tokens=200,
            temperature=0,
            system=_SCORING_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except Exception as exc:
        logger.warning(
            "Scoring failed for url=%s model=%s error=%s",
            item.get("url", ""),
            _MODEL,
            exc,
        )
        return None

    raw = response.content[0].text.strip() if response.content else ""

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

    # CHANGE 2: Validate score/tag/summary consistency before accepting output.
    if not _validate_scoring_output(score=score, tags=tags, summary=summary, article=item):
        logger.warning("Failed scoring validation for url=%s score=%s tags=%s", item.get("url", ""), score, tags)
        return None

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


def run_analysis_pipeline(articles: list[dict]) -> dict[str, list[dict]]:
    """Run two-stage relevance/scoring and return kept + all analyzed articles."""
    if not articles:
        logger.info("Analysis pipeline received no articles; nothing to do")
        return {"final_articles": [], "all_articles": []}

    relevant_articles: list[dict] = []
    all_articles: list[dict] = []

    for article in articles:
        if is_relevant(article):
            relevant_articles.append(article)
        else:
            all_articles.append(
                {
                    **article,
                    "score": 0,
                    "raw_score": 0,
                    "passed_relevance_filter": False,
                    "kept": False,
                    "rejection_reason": "failed_relevance_filter",
                }
            )

    logger.info("Analysis stage 1 complete: relevant=%s total=%s", len(relevant_articles), len(articles))

    scored_results: list[dict] = []
    for article in relevant_articles:
        scored = score_and_summarize(article)
        if scored is not None:
            scored_results.append(scored)
        else:
            all_articles.append(
                {
                    **article,
                    "score": 0,
                    "raw_score": 0,
                    "passed_relevance_filter": True,
                    "kept": False,
                    "rejection_reason": "score_below_threshold",
                }
            )

    logger.info("Analysis stage 2 complete: scored_successfully=%s", len(scored_results))

    before_score_filter = len(scored_results)
    high_impact: list[dict] = []
    for item in scored_results:
        score = int(item.get("score", 0))
        enriched = {
            **item,
            "raw_score": score,
            "passed_relevance_filter": True,
            "kept": score >= 6,
            "rejection_reason": None if score >= 6 else "score_below_threshold",
        }
        all_articles.append(enriched)
        if score >= 6:
            high_impact.append(enriched)

    dropped_low_score = before_score_filter - len(high_impact)
    logger.info("Analysis score filter complete: dropped_low_score=%s", dropped_low_score)

    high_impact.sort(key=lambda x: int(x.get("score", 0)), reverse=True)
    final = high_impact[:10]

    if not final:
        logger.warning("Analysis pipeline produced no final articles")
        return {"final_articles": [], "all_articles": all_articles}

    logger.info("Analysis pipeline complete: final_output=%s", len(final))

    # TODO: Pass analyzed results to report persistence service.
    return {"final_articles": final, "all_articles": all_articles}


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
