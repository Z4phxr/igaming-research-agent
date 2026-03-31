"""RAG-style daily intelligence briefing generator from top scored articles."""

import logging
import os
from typing import Optional

from anthropic import Anthropic
from sqlalchemy.orm import Session

from app.services.prompt_manager import (
    PROMPT_KEY_BRIEFING_SYSTEM,
    get_active_prompt_content,
)

logger = logging.getLogger(__name__)

_anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
if not _anthropic_api_key:
    raise RuntimeError("ANTHROPIC_API_KEY is missing.")

anthropic_client = Anthropic(api_key=_anthropic_api_key)

_SYSTEM_PROMPT_FALLBACK = """
You are a news intelligence analyst for USA iGaming journalists. 
Your job is to synthesize daily news into a briefing that journalists 
can use as research for their own articles.

Focus on the most interesting and impactful stories. Highlight novelty, 
conflict, and business consequences. Avoid filler and generic analysis.

Structure your briefing EXACTLY like this:

## Top Stories This Week 

**[Article Title]** — [CATEGORY] | Score: X/10
- What happened: One sentence of clear, specific facts
- Why it matters: One sentence on business/regulatory impact
- Story angle for journalists: One sentence on what makes this newsworthy

**[Article Title]** — [CATEGORY] | Score: X/10
- What happened: One sentence of clear, specific facts
- Why it matters: One sentence on business/regulatory impact
- Story angle for journalists: One sentence on what makes this newsworthy

(Repeat for each article, ordered by score descending)

## Key Themes Emerging Today
- [Theme 1]: List which articles relate to it
- [Theme 2]: List which articles relate to it
- [Theme 3]: List which articles relate to it

## Companies & States In The News Today
- [Company/State]: Mentioned in X articles, context
- [Company/State]: Mentioned in X articles, context
- [Company/State]: Mentioned in X articles, context
"""


def generate_briefing(articles: list[dict], db: Session | None = None) -> Optional[str]:
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
        system_prompt = get_active_prompt_content(db, PROMPT_KEY_BRIEFING_SYSTEM, _SYSTEM_PROMPT_FALLBACK)
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1500,
            temperature=0.3,
            system=system_prompt,
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
