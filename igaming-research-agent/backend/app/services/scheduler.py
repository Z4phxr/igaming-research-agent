"""Daily pipeline scheduler using APScheduler.

Runs flow: active queries -> search -> scrape -> analyze -> persist report.
TODO: Add robust logging/telemetry and retry strategy per step.
"""

import datetime
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Article, Report
from app.services.analyzer import run_analysis_pipeline
from app.services.report_generator import generate_briefing
from app.services.scraper import scrape_articles
from app.services.search import run_search_pipeline

logger = logging.getLogger(__name__)
_scheduler = BackgroundScheduler(timezone="UTC")


def _normalize_utc_naive(value: datetime.datetime) -> datetime.datetime:
    """Normalize datetime to naive UTC for DB consistency."""
    if value.tzinfo is None:
        return value
    return value.astimezone(datetime.timezone.utc).replace(tzinfo=None)


def _parse_published_date(value: object) -> datetime.datetime | None:
    """Parse provider published_date values into naive UTC datetime."""
    if value is None:
        return None

    if isinstance(value, datetime.datetime):
        return _normalize_utc_naive(value)

    if isinstance(value, datetime.date):
        return datetime.datetime(value.year, value.month, value.day)

    if not isinstance(value, str):
        return None

    raw = value.strip()
    if not raw:
        return None

    iso_candidates = [raw]
    if raw.endswith("Z"):
        iso_candidates.append(raw[:-1] + "+00:00")

    for candidate in iso_candidates:
        try:
            parsed = datetime.datetime.fromisoformat(candidate)
            return _normalize_utc_naive(parsed)
        except ValueError:
            pass

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            parsed = datetime.datetime.strptime(raw, fmt)
            return _normalize_utc_naive(parsed)
        except ValueError:
            continue

    return None


def _reject_article(article: dict, reason: str) -> dict:
    """Build a consistent rejected article payload for persistence/reporting."""
    return {
        **article,
        "score": 0,
        "raw_score": 0,
        "passed_relevance_filter": False,
        "kept": False,
        "rejection_reason": reason,
    }


def _split_recent_articles(
    articles: list[dict],
    now_utc: datetime.datetime,
) -> tuple[list[dict], list[dict]]:
    """Split articles by strict 24h freshness policy using published_date."""
    cutoff = now_utc - datetime.timedelta(hours=24)
    recent: list[dict] = []
    rejected: list[dict] = []

    for article in articles:
        raw_value = article.get("published_date")
        if raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()):
            rejected.append(_reject_article(article, "missing_published_date"))
            continue

        published_at = _parse_published_date(raw_value)
        if published_at is None:
            rejected.append(_reject_article(article, "invalid_published_date"))
            continue

        if published_at > now_utc:
            rejected.append(_reject_article(article, "future_published_date"))
            continue

        if published_at < cutoff:
            rejected.append(_reject_article(article, "stale_published_date"))
            continue

        recent.append({**article, "published_date": published_at})

    return recent, rejected


def run_daily_pipeline(db: Session | None = None, raise_on_error: bool = False) -> None:
    """Execute the full daily research pipeline.

    TODO: Break this into smaller orchestration functions and add metrics.
    """
    owns_session = False
    session = db
    if session is None:
        session = SessionLocal()
        owns_session = True

    try:
        logger.info("Daily pipeline started")
        pipeline_now = datetime.datetime.utcnow()

        raw_articles = run_search_pipeline(session)
        logger.info("Daily pipeline step search complete: count=%s", len(raw_articles))
        if not raw_articles:
            logger.warning("Daily pipeline search returned no articles")

        scraped_articles = scrape_articles(raw_articles)
        logger.info("Daily pipeline step scrape complete: count=%s", len(scraped_articles))
        if not scraped_articles:
            logger.warning("Daily pipeline scrape returned no articles")

        recent_articles, freshness_rejections = _split_recent_articles(scraped_articles, pipeline_now)
        logger.info(
            "Daily pipeline step freshness complete: recent=%s rejected=%s",
            len(recent_articles),
            len(freshness_rejections),
        )
        if not recent_articles:
            logger.warning("Daily pipeline freshness gate rejected all scraped articles")

        analysis_result = run_analysis_pipeline(recent_articles)
        final_articles = analysis_result.get("final_articles", [])
        all_articles = freshness_rejections + analysis_result.get("all_articles", [])
        logger.info("Daily pipeline step analysis complete: count=%s", len(final_articles))
        if not final_articles:
            logger.warning("Daily pipeline analysis returned no final articles")

        briefing_text = generate_briefing(final_articles)
        briefing_generated_at = None
        if briefing_text is None:
            logger.warning("Briefing generation failed or returned empty; saving blank briefing")
            briefing_text = ""
        else:
            briefing_generated_at = datetime.datetime.utcnow()
            logger.info("Briefing generated successfully")

        persisted_articles: list[Article] = []
        for item in all_articles:
            url = str(item.get("url", "")).strip()
            if not url:
                continue

            published_date = _parse_published_date(item.get("published_date"))

            existing = session.query(Article).filter(Article.url == url).first()
            if existing:
                # Refresh mutable fields when URL already exists.
                existing.title = str(item.get("title") or existing.title)
                existing.source_domain = str(item.get("source_domain") or existing.source_domain)
                existing.summary = str(item.get("summary") or item.get("snippet") or existing.summary)
                existing.full_text = str(item.get("full_text") or existing.full_text)
                existing.score = int(item.get("score", existing.score or 0))
                existing.raw_score = int(item.get("raw_score", existing.raw_score or 0))
                existing.passed_relevance_filter = bool(
                    item.get("passed_relevance_filter", existing.passed_relevance_filter)
                )
                existing.kept = bool(item.get("kept", existing.kept))
                existing.rejection_reason = item.get("rejection_reason")
                existing.tags = str(item.get("tags") or existing.tags)
                if published_date is not None:
                    existing.published_date = published_date
                existing.scraped_date = datetime.datetime.utcnow()
                persisted_articles.append(existing)
                continue

            article = Article(
                title=str(item.get("title") or "Untitled"),
                url=url,
                source_domain=str(item.get("source_domain") or ""),
                summary=str(item.get("summary") or item.get("snippet") or ""),
                full_text=str(item.get("full_text") or ""),
                score=int(item.get("score", 0)),
                raw_score=int(item.get("raw_score", item.get("score", 0))),
                passed_relevance_filter=bool(item.get("passed_relevance_filter", True)),
                kept=bool(item.get("kept", int(item.get("score", 0)) >= 6)),
                rejection_reason=item.get("rejection_reason"),
                tags=str(item.get("tags") or ""),
                matched_query_id=item.get("matched_query_id"),
                published_date=published_date,
                scraped_date=datetime.datetime.utcnow(),
                created_at=datetime.datetime.utcnow(),
            )
            session.add(article)
            session.flush()
            persisted_articles.append(article)

        report = Report(
            report_date=datetime.date.today(),
            total_articles_found=len(raw_articles),
            total_articles_kept=sum(1 for item in all_articles if item.get("kept")),
            briefing=briefing_text,
            briefing_generated_at=briefing_generated_at,
            generated_at=datetime.datetime.utcnow(),
            articles=persisted_articles,
        )
        session.add(report)
        session.commit()

        logger.info(
            "Daily pipeline complete: found=%s scraped=%s analyzed=%s saved=%s",
            len(raw_articles),
            len(scraped_articles),
            len(final_articles),
            len(persisted_articles),
        )

    except Exception as exc:
        session.rollback()
        logger.exception("Daily pipeline failed with unhandled exception")
        if raise_on_error:
            raise exc
    finally:
        if owns_session:
            session.close()


def start_scheduler() -> None:
    """Start APScheduler daily cron task.

    TODO: Prevent duplicate scheduling in multi-worker deployment.
    """
    if _scheduler.running:
        return

    _scheduler.add_job(
        run_daily_pipeline,
        trigger=CronTrigger(hour=7, minute=0, timezone="UTC"),
        id="daily_pipeline",
        replace_existing=True,
    )
    _scheduler.start()


def stop_scheduler() -> None:
    """Stop APScheduler gracefully.

    TODO: Flush in-flight run metadata before shutdown.
    """
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
