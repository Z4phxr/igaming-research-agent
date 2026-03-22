"""RAG-style daily intelligence briefing generator from top scored articles."""

import logging
import os
from typing import Optional

from anthropic import Anthropic

logger = logging.getLogger(__name__)

_anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
if not _anthropic_api_key:
    raise RuntimeError("ANTHROPIC_API_KEY is missing.")

anthropic_client = Anthropic(api_key=_anthropic_api_key)

_SYSTEM_PROMPT = """
You are a senior intelligence analyst for a USA iGaming 
investment research firm. Your job is to write a concise, 
professional daily briefing based on today's top news stories.

Write in a clear, authoritative tone. Be specific about 
business implications. Avoid generic statements.

Structure your briefing EXACTLY like this:

## Executive Summary
2-3 sentences synthesizing the most important theme 
of today's news and its market implications.

## Key Developments
For each article (ordered by importance):
**[CATEGORY TAG] — [Article Title]** (Score: X/10)
2-3 sentences expanding on business impact beyond 
the summary. Include specific implications for 
operators, investors, or regulators.

## Market Implications
2-3 sentences about what these developments mean 
collectively for the US iGaming market this week.

## Companies & Entities To Watch
Bullet list of specific companies, regulators, or 
states mentioned that investors should monitor.
"""


def generate_briefing(articles: list[dict]) -> Optional[str]:
    """Generate a polished briefing narrative from top scored articles."""
    if not articles:
        return None

    parts: list[str] = []
    for article in articles:
        parts.append("---")
        parts.append(f"SCORE: {article.get('score', 0)}/10")
        parts.append(f"TITLE: {str(article.get('title', '')).strip()}")
        parts.append(f"SOURCE: {str(article.get('source_domain', '')).strip()}")
        parts.append(f"TAGS: {str(article.get('tags', '')).strip()}")
        parts.append(f"SUMMARY: {str(article.get('summary', '')).strip()}")
        parts.append("---")

    context_string = "\n".join(parts)

    try:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1500,
            temperature=0.3,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Today's top iGaming stories:\n\n{context_string}"}],
        )
    except Exception as exc:
        logger.warning("Briefing generation failed: %s", exc)
        return None

    text = response.content[0].text.strip() if getattr(response, "content", None) else ""
    if not text:
        logger.warning("Briefing generation returned empty response")
        return None

    return text
