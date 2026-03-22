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
from app.services.scraper import scrape_articles
from app.services.search import run_search_pipeline

logger = logging.getLogger(__name__)
_scheduler = BackgroundScheduler(timezone="UTC")


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

        raw_articles = run_search_pipeline(session)
        logger.info("Daily pipeline step search complete: count=%s", len(raw_articles))
        if not raw_articles:
            logger.warning("Daily pipeline search returned no articles")

        scraped_articles = scrape_articles(raw_articles)
        logger.info("Daily pipeline step scrape complete: count=%s", len(scraped_articles))
        if not scraped_articles:
            logger.warning("Daily pipeline scrape returned no articles")

        analysis_result = run_analysis_pipeline(scraped_articles)
        final_articles = analysis_result.get("final_articles", [])
        all_articles = analysis_result.get("all_articles", [])
        logger.info("Daily pipeline step analysis complete: count=%s", len(final_articles))
        if not final_articles:
            logger.warning("Daily pipeline analysis returned no final articles")

        persisted_articles: list[Article] = []
        for item in all_articles:
            url = str(item.get("url", "")).strip()
            if not url:
                continue

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
