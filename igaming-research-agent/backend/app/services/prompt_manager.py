"""Prompt manager service for editable, versioned LLM prompt templates."""

import datetime
from typing import Optional

from sqlalchemy.orm import Session, selectinload

from app.models import PromptTemplate, PromptTemplateVersion

PROMPT_KEY_RELEVANCE_SYSTEM = "analyzer.relevance_system"
PROMPT_KEY_SCORING_SYSTEM = "analyzer.scoring_system"
PROMPT_KEY_REJECTION_EXPLAIN_SYSTEM = "analyzer.rejection_explain_system"
PROMPT_KEY_BRIEFING_SYSTEM = "report_generator.briefing_system"

DEFAULT_PROMPTS: dict[str, dict[str, str]] = {
    PROMPT_KEY_RELEVANCE_SYSTEM: {
        "title": "Analyzer Relevance System Prompt",
        "description": "Stage-1 YES/NO relevance gate for US iGaming filtering.",
        "content": """
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
""".strip(),
    },
    PROMPT_KEY_SCORING_SYSTEM: {
        "title": "Analyzer Scoring System Prompt",
        "description": "Stage-2 scoring, summary, and tagging rubric.",
        "content": """
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
""".strip(),
    },
    PROMPT_KEY_REJECTION_EXPLAIN_SYSTEM: {
        "title": "Analyzer Rejection Explain Prompt",
        "description": "Optional deep explanation for rejected relevance/scoring items.",
        "content": """
You explain why an article was rejected in an iGaming research pipeline.
Be specific, concise, and factual.

Rules:
- Return 1-2 short sentences only.
- Mention the stage (relevance or scoring).
- Mention the concrete trigger (e.g., non-US focus, no policy/business signal, score below 6, malformed scoring output).
- Do not mention model internals or policies.
""".strip(),
    },
    PROMPT_KEY_BRIEFING_SYSTEM: {
        "title": "Report Generator Briefing Prompt",
        "description": "Narrative briefing synthesis prompt for top scored stories.",
        "content": """
You are a news intelligence analyst for USA iGaming journalists.
Your job is to synthesize daily news into a briefing that journalists
can use as research for their own articles.

Focus on the most interesting and impactful stories. Highlight novelty,
conflict, and business consequences. Avoid filler and generic analysis.

Structure your briefing EXACTLY like this:

## Top Stories This Week

**[Article Title]** - [CATEGORY] | Score: X/10
- What happened: One sentence of clear, specific facts
- Why it matters: One sentence on business/regulatory impact
- Story angle for journalists: One sentence on what makes this newsworthy

**[Article Title]** - [CATEGORY] | Score: X/10
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
""".strip(),
    },
}


def ensure_default_prompt_templates(db: Session) -> None:
    """Seed default prompts if missing, preserving existing edits."""
    now = datetime.datetime.utcnow()

    for key, default in DEFAULT_PROMPTS.items():
        template = db.query(PromptTemplate).filter(PromptTemplate.key == key).first()
        if template is None:
            template = PromptTemplate(
                key=key,
                title=default["title"],
                description=default["description"],
                draft_content=default["content"],
                active_content=default["content"],
                active_version=1,
                created_at=now,
                updated_at=now,
            )
            db.add(template)
            db.flush()
            db.add(
                PromptTemplateVersion(
                    prompt_template_id=template.id,
                    version=1,
                    content=default["content"],
                    is_active=True,
                    created_at=now,
                )
            )
            continue

        changed = False
        if not template.title:
            template.title = default["title"]
            changed = True
        if not template.description:
            template.description = default["description"]
            changed = True
        if not template.active_content:
            template.active_content = default["content"]
            changed = True
        if not template.draft_content:
            template.draft_content = template.active_content
            changed = True

        versions_count = (
            db.query(PromptTemplateVersion)
            .filter(PromptTemplateVersion.prompt_template_id == template.id)
            .count()
        )
        if versions_count == 0:
            db.add(
                PromptTemplateVersion(
                    prompt_template_id=template.id,
                    version=max(int(template.active_version or 1), 1),
                    content=template.active_content,
                    is_active=True,
                    created_at=now,
                )
            )
            changed = True

        if changed:
            template.updated_at = now


def list_templates(db: Session) -> list[PromptTemplate]:
    return db.query(PromptTemplate).order_by(PromptTemplate.key.asc()).all()


def get_template(db: Session, key: str) -> Optional[PromptTemplate]:
    return (
        db.query(PromptTemplate)
        .options(selectinload(PromptTemplate.versions))
        .filter(PromptTemplate.key == key)
        .first()
    )


def save_draft(db: Session, key: str, draft_content: str) -> Optional[PromptTemplate]:
    template = db.query(PromptTemplate).filter(PromptTemplate.key == key).first()
    if template is None:
        return None

    template.draft_content = draft_content
    template.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(template)
    return template


def publish(db: Session, key: str, content: Optional[str] = None) -> Optional[PromptTemplate]:
    template = db.query(PromptTemplate).filter(PromptTemplate.key == key).first()
    if template is None:
        return None

    publish_content = (content if content is not None else template.draft_content).strip()
    if not publish_content:
        return None

    next_version = int(template.active_version or 0) + 1

    db.query(PromptTemplateVersion).filter(
        PromptTemplateVersion.prompt_template_id == template.id,
        PromptTemplateVersion.is_active.is_(True),
    ).update({"is_active": False}, synchronize_session=False)

    version = PromptTemplateVersion(
        prompt_template_id=template.id,
        version=next_version,
        content=publish_content,
        is_active=True,
        created_at=datetime.datetime.utcnow(),
    )
    db.add(version)

    template.active_content = publish_content
    template.draft_content = publish_content
    template.active_version = next_version
    template.updated_at = datetime.datetime.utcnow()

    db.commit()
    db.refresh(template)
    return template


def list_history(db: Session, key: str) -> Optional[list[PromptTemplateVersion]]:
    template = db.query(PromptTemplate).filter(PromptTemplate.key == key).first()
    if template is None:
        return None

    return (
        db.query(PromptTemplateVersion)
        .filter(PromptTemplateVersion.prompt_template_id == template.id)
        .order_by(PromptTemplateVersion.version.desc())
        .all()
    )


def get_active_prompt_content(db: Optional[Session], key: str, fallback: str) -> str:
    """Resolve prompt content from DB, falling back safely to code defaults."""
    if db is None:
        return fallback

    template = db.query(PromptTemplate).filter(PromptTemplate.key == key).first()
    if template is None:
        return fallback

    content = str(template.active_content or "").strip()
    return content or fallback
