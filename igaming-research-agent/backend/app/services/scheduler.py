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
from app.services.release_discovery import discover_recent_releases
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


def _persist_articles(session: Session, items: list[dict]) -> list[Article]:
    """Create or update articles by URL and return persisted rows."""
    persisted_articles: list[Article] = []

    for item in items:
        url = str(item.get("url", "")).strip()
        if not url:
            continue

        published_date = _parse_published_date(item.get("published_date"))

        existing = session.query(Article).filter(Article.url == url).first()
        if existing:
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
            existing.article_type = str(item.get("article_type") or existing.article_type or "top_story")
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
            article_type=str(item.get("article_type") or "top_story"),
            matched_query_id=item.get("matched_query_id"),
            published_date=published_date,
            scraped_date=datetime.datetime.utcnow(),
            created_at=datetime.datetime.utcnow(),
        )
        session.add(article)
        session.flush()
        persisted_articles.append(article)

    return persisted_articles


def _get_or_create_daily_report(session: Session, report_date: datetime.date) -> Report:
    """Reuse today's report when present, otherwise create one."""
    report = (
        session.query(Report)
        .filter(Report.report_date == report_date)
        .order_by(Report.generated_at.desc(), Report.id.desc())
        .first()
    )
    if report is not None:
        return report

    report = Report(
        report_date=report_date,
        total_articles_found=0,
        total_articles_kept=0,
        briefing="",
        briefing_generated_at=None,
        generated_at=datetime.datetime.utcnow(),
        articles=[],
    )
    session.add(report)
    session.flush()
    return report


def _attach_report_articles(report: Report, persisted_articles: list[Article]) -> None:
    """Attach articles to report without duplicating report-article pairs."""
    existing_ids = {article.id for article in report.articles if article.id is not None}
    for article in persisted_articles:
        if article.id in existing_ids:
            continue
        report.articles.append(article)
        if article.id is not None:
            existing_ids.add(article.id)


def run_articles_pipeline(db: Session | None = None, raise_on_error: bool = False) -> dict:
    """Execute only the article research flow (search/scrape/analyze)."""
    owns_session = False
    session = db
    if session is None:
        session = SessionLocal()
        owns_session = True

    try:
        logger.info("Articles pipeline started")
        pipeline_now = datetime.datetime.utcnow()

        raw_articles = run_search_pipeline(session)
        logger.info("Articles pipeline step search complete: count=%s", len(raw_articles))
        if not raw_articles:
            logger.warning("Articles pipeline search returned no articles")

        scraped_articles = scrape_articles(raw_articles)
        logger.info("Articles pipeline step scrape complete: count=%s", len(scraped_articles))
        if not scraped_articles:
            logger.warning("Articles pipeline scrape returned no articles")

        recent_articles, freshness_rejections = _split_recent_articles(scraped_articles, pipeline_now)
        logger.info(
            "Articles pipeline step freshness complete: recent=%s rejected=%s",
            len(recent_articles),
            len(freshness_rejections),
        )
        if not recent_articles:
            logger.warning("Daily pipeline freshness gate rejected all scraped articles")

        analysis_result = run_analysis_pipeline(recent_articles)
        final_articles = analysis_result.get("final_articles", [])
        all_articles = freshness_rejections + analysis_result.get("all_articles", [])
        logger.info("Articles pipeline step analysis complete: count=%s", len(final_articles))
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

        persisted_articles = _persist_articles(session, all_articles)

        report = _get_or_create_daily_report(session, report_date=datetime.date.today())
        report.total_articles_found = len(raw_articles)
        report.total_articles_kept = sum(1 for item in all_articles if item.get("kept"))
        report.briefing = briefing_text
        report.briefing_generated_at = briefing_generated_at
        report.generated_at = datetime.datetime.utcnow()
        _attach_report_articles(report, persisted_articles)

        session.commit()

        logger.info(
            "Articles pipeline complete: found=%s scraped=%s analyzed=%s saved=%s",
            len(raw_articles),
            len(scraped_articles),
            len(final_articles),
            len(persisted_articles),
        )
        return {
            "articles_found": len(raw_articles),
            "articles_saved": len(persisted_articles),
            "report_id": report.id,
        }
    except Exception as exc:
        session.rollback()
        logger.exception("Articles pipeline failed with unhandled exception")
        if raise_on_error:
            raise exc
        return {"articles_found": 0, "articles_saved": 0, "report_id": None}
    finally:
        if owns_session:
            session.close()


def run_release_pipeline(db: Session | None = None, raise_on_error: bool = False) -> dict:
    """Execute only the release discovery flow."""
    owns_session = False
    session = db
    if session is None:
        session = SessionLocal()
        owns_session = True

    try:
        logger.info("Release pipeline started")
        pipeline_now = datetime.datetime.utcnow()

        release_articles = discover_recent_releases(session, now_utc=pipeline_now)
        logger.info("Release pipeline discovery complete: count=%s", len(release_articles))

        persisted_articles = _persist_articles(session, release_articles)

        report = _get_or_create_daily_report(session, report_date=datetime.date.today())
        report.generated_at = datetime.datetime.utcnow()
        _attach_report_articles(report, persisted_articles)

        session.commit()
        logger.info("Release pipeline complete: discovered=%s saved=%s", len(release_articles), len(persisted_articles))
        return {
            "releases_found": len(release_articles),
            "releases_saved": len(persisted_articles),
            "report_id": report.id,
        }
    except Exception as exc:
        session.rollback()
        logger.exception("Release pipeline failed with unhandled exception")
        if raise_on_error:
            raise exc
        return {"releases_found": 0, "releases_saved": 0, "report_id": None}
    finally:
        if owns_session:
            session.close()


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
        run_articles_pipeline(session, raise_on_error=raise_on_error)
        run_release_pipeline(session, raise_on_error=raise_on_error)
        logger.info("Daily pipeline complete")
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

    def _safe_add_job(func, job_id: str) -> None:
        try:
            _scheduler.add_job(
                func,
                trigger=CronTrigger(hour=7, minute=0, timezone="UTC"),
                id=job_id,
                replace_existing=True,
                coalesce=True,
                max_instances=1,
            )
        except TypeError:
            # Compatibility with lightweight test doubles that do not accept APScheduler kwargs.
            _scheduler.add_job(
                func,
                trigger=CronTrigger(hour=7, minute=0, timezone="UTC"),
                id=job_id,
                replace_existing=True,
            )

    _safe_add_job(run_articles_pipeline, "daily_articles_pipeline")
    _safe_add_job(run_release_pipeline, "daily_releases_pipeline")
    _scheduler.start()


def stop_scheduler() -> None:
    """Stop APScheduler gracefully.

    TODO: Flush in-flight run metadata before shutdown.
    """
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
