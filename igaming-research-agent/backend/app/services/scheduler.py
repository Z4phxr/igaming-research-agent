"""Daily pipeline scheduler using APScheduler.

Runs flow: active queries -> search -> scrape -> analyze -> persist report.
TODO: Add robust logging/telemetry and retry strategy per step.
"""

import datetime
import email.utils
import logging
import re
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Article, Report
from app.models import PipelineSettings as PipelineSettingsModel
from app.services.analyzer import infer_published_date_with_llm, run_analysis_pipeline
from app.services.release_discovery import discover_recent_releases
from app.services.report_generator import generate_briefing
from app.services.scraper import scrape_articles
from app.services.search import run_search_pipeline

logger = logging.getLogger(__name__)
_scheduler = BackgroundScheduler(timezone="UTC")
DATE_CHECK_FAILED_REASON = "Rejected: fail to check the date"

_US_TIMEZONE_BY_ABBR = {
    "ET": "America/New_York",
    "EST": "America/New_York",
    "EDT": "America/New_York",
    "CT": "America/Chicago",
    "CST": "America/Chicago",
    "CDT": "America/Chicago",
    "MT": "America/Denver",
    "MST": "America/Denver",
    "MDT": "America/Denver",
    "PT": "America/Los_Angeles",
    "PST": "America/Los_Angeles",
    "PDT": "America/Los_Angeles",
}


def _normalize_utc_naive(value: datetime.datetime) -> datetime.datetime:
    """Normalize datetime to naive UTC for DB consistency."""
    if value.tzinfo is None:
        return value
    return value.astimezone(datetime.timezone.utc).replace(tzinfo=None)


def _parse_relative_datetime(raw: str, now_utc: datetime.datetime) -> datetime.datetime | None:
    """Parse common relative datetime phrases from news providers.

    Examples: "2 hours ago", "15 minutes ago", "yesterday".
    """
    lower = raw.strip().lower()
    if not lower:
        return None

    if lower in {"yesterday", "1 day ago"}:
        return now_utc - datetime.timedelta(days=1)

    match = re.match(r"^(\d+)\s+(minute|minutes|hour|hours|day|days|week|weeks)\s+ago$", lower)
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)

    if "minute" in unit:
        return now_utc - datetime.timedelta(minutes=amount)
    if "hour" in unit:
        return now_utc - datetime.timedelta(hours=amount)
    if "day" in unit:
        return now_utc - datetime.timedelta(days=amount)
    if "week" in unit:
        return now_utc - datetime.timedelta(weeks=amount)

    return None


def _parse_named_timezone_datetime(raw: str) -> datetime.datetime | None:
    """Parse datetime strings ending with common timezone abbreviations.

    Example: "Mar 30, 2026, 09:00 AM ET"
    """
    match = re.match(r"^(?P<base>.+?)\s+(?P<tz>[A-Za-z]{2,4})$", raw.strip())
    if not match:
        return None

    base_value = match.group("base").strip().rstrip(",")
    tz_token = match.group("tz").upper()

    if tz_token in {"UTC", "GMT"}:
        tzinfo = datetime.timezone.utc
    else:
        timezone_name = _US_TIMEZONE_BY_ABBR.get(tz_token)
        if not timezone_name:
            return None
        tzinfo = ZoneInfo(timezone_name)

    for fmt in (
        "%b %d, %Y, %I:%M %p",
        "%B %d, %Y, %I:%M %p",
        "%b %d %Y %I:%M %p",
        "%B %d %Y %I:%M %p",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
    ):
        try:
            parsed = datetime.datetime.strptime(base_value, fmt)
            return _normalize_utc_naive(parsed.replace(tzinfo=tzinfo))
        except ValueError:
            continue

    return None


def _parse_published_date(
    value: object,
    now_utc: datetime.datetime | None = None,
) -> datetime.datetime | None:
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

    reference_now = now_utc or datetime.datetime.utcnow()
    relative = _parse_relative_datetime(raw, reference_now)
    if relative is not None:
        return _normalize_utc_naive(relative)

    named_tz_parsed = _parse_named_timezone_datetime(raw)
    if named_tz_parsed is not None:
        return named_tz_parsed

    iso_candidates = [raw]
    if raw.endswith("Z"):
        iso_candidates.append(raw[:-1] + "+00:00")

    for candidate in iso_candidates:
        try:
            parsed = datetime.datetime.fromisoformat(candidate)
            return _normalize_utc_naive(parsed)
        except ValueError:
            pass

    # Handle RFC-2822 style timestamps, e.g. "Tue, 31 Mar 2026 14:12:00 GMT".
    try:
        parsed = email.utils.parsedate_to_datetime(raw)
        if parsed is not None:
            return _normalize_utc_naive(parsed)
    except (TypeError, ValueError):
        pass

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            parsed = datetime.datetime.strptime(raw, fmt)
            return _normalize_utc_naive(parsed)
        except ValueError:
            continue

    for fmt in (
        "%b %d, %Y, %I:%M %p",
        "%B %d, %Y, %I:%M %p",
        "%b %d %Y %I:%M %p",
        "%B %d %Y %I:%M %p",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
    ):
        try:
            parsed = datetime.datetime.strptime(raw, fmt)
            return _normalize_utc_naive(parsed)
        except ValueError:
            continue

    for fmt in ("%b %d, %Y", "%B %d, %Y", "%b %d %Y", "%B %d %Y"):
        try:
            parsed = datetime.datetime.strptime(raw, fmt)
            return _normalize_utc_naive(parsed)
        except ValueError:
            continue

    return None


def _extract_date_candidates_from_text(text: str, max_candidates: int = 30) -> list[str]:
    """Extract potential date strings from arbitrary text."""
    if not text:
        return []

    candidates: list[str] = []
    patterns = [
        r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b",
        r"\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b",
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b",
        r"\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{4}\b",
    ]

    for pattern in patterns:
        for match in re.findall(pattern, text, flags=re.IGNORECASE):
            value = str(match).strip()
            if value and value not in candidates:
                candidates.append(value)
            if len(candidates) >= max_candidates:
                return candidates

    return candidates


def _extract_date_candidates_from_url(url: str) -> list[str]:
    """Extract potential date tokens from URL paths."""
    if not url:
        return []

    candidates: list[str] = []
    patterns = [
        r"/(\d{4})/(\d{1,2})/(\d{1,2})(?:/|$)",
        r"/(\d{4})-(\d{1,2})-(\d{1,2})(?:/|$)",
        r"/(\d{4})_(\d{1,2})_(\d{1,2})(?:/|$)",
    ]

    for pattern in patterns:
        for year, month, day in re.findall(pattern, url):
            token = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
            if token not in candidates:
                candidates.append(token)

    return candidates


def _infer_article_published_date(
    article: dict,
    now_utc: datetime.datetime,
    db: Session | None = None,
) -> tuple[datetime.datetime | None, str | None]:
    """Infer article published date with deterministic parsing then LLM fallback.

    LLM fallback is only used when deterministic extraction fails.
    """
    field_candidates = [
        article.get("published_date"),
        article.get("date"),
        article.get("publication_date"),
        article.get("pub_date"),
        article.get("publishedAt"),
    ]

    for value in field_candidates:
        parsed = _parse_published_date(value, now_utc=now_utc)
        if parsed is not None:
            return parsed, "provider"

    url = str(article.get("url") or "").strip()
    for token in _extract_date_candidates_from_url(url):
        parsed = _parse_published_date(token, now_utc=now_utc)
        if parsed is not None:
            return parsed, "url"

    text_candidates: list[str] = []
    for field in ("title", "snippet", "full_text"):
        value = str(article.get(field) or "").strip()
        if not value:
            continue
        sample = value[:5000] if field == "full_text" else value
        text_candidates.extend(_extract_date_candidates_from_text(sample))
        if len(text_candidates) >= 30:
            break

    for token in text_candidates:
        parsed = _parse_published_date(token, now_utc=now_utc)
        if parsed is not None:
            return parsed, "text"

    llm_date_value = infer_published_date_with_llm(article, now_utc=now_utc, db=db)
    if llm_date_value is not None:
        parsed = _parse_published_date(llm_date_value, now_utc=now_utc)
        if parsed is not None:
            return parsed, "llm"

    return None, None


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
    db: Session | None = None,
) -> tuple[list[dict], list[dict]]:
    """Pass all articles through to analysis.

    Serper already filters to 24-hour window via qdr:d parameter,
    so we trust upstream filtering and don't apply secondary date gates.
    All articles are returned as accepted; none are rejected by date.
    """
    recent: list[dict] = []

    for article in articles:
        published_at, date_source = _infer_article_published_date(article, now_utc=now_utc, db=db)
        recent.append(
            {
                **article,
                "published_date": published_at,
                "date_inference_source": date_source or "upstream_window",
            }
        )

    return recent, []


def _persist_articles(session: Session, items: list[dict]) -> list[Article]:
    """Create or update articles by URL and return persisted rows."""
    persisted_articles: list[Article] = []

    for item in items:
        url = str(item.get("url", "")).strip()
        if not url:
            continue

        published_date = _parse_published_date(item.get("published_date"))
        date_inference_source = str(item.get("date_inference_source") or "")
        if date_inference_source == "llm" and published_date is not None:
            logger.info(
                "Article published_date inferred by LLM fallback url=%s published_date=%s",
                url,
                published_date.isoformat(),
            )

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
        articles_pipeline_ran_at=None,
        releases_pipeline_ran_at=None,
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

        recent_articles, freshness_rejections = _split_recent_articles(scraped_articles, pipeline_now, db=session)
        logger.info(
            "Articles pipeline step freshness complete: recent=%s rejected=%s",
            len(recent_articles),
            len(freshness_rejections),
        )
        if freshness_rejections:
            rejection_breakdown: dict[str, int] = {}
            for item in freshness_rejections:
                reason = str(item.get("rejection_reason") or "unknown")
                rejection_breakdown[reason] = rejection_breakdown.get(reason, 0) + 1
            logger.info("Articles pipeline freshness rejections by reason: %s", rejection_breakdown)
        if not recent_articles:
            logger.warning("Daily pipeline freshness gate rejected all scraped articles")

        try:
            analysis_result = run_analysis_pipeline(recent_articles, db=session)
        except TypeError as exc:
            # Backward compatibility for tests or callers monkeypatching
            # run_analysis_pipeline(articles) without a db keyword.
            if "unexpected keyword argument 'db'" not in str(exc):
                raise
            analysis_result = run_analysis_pipeline(recent_articles)
        final_articles = analysis_result.get("final_articles", [])
        all_articles = freshness_rejections + analysis_result.get("all_articles", [])
        logger.info("Articles pipeline step analysis complete: count=%s", len(final_articles))
        if not final_articles:
            logger.warning("Daily pipeline analysis returned no final articles")

        briefing_text = generate_briefing(final_articles, db=session)
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
        report.articles_pipeline_ran_at = datetime.datetime.utcnow()
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
        configured_window_hours = int(getattr(settings, "release_recent_window_hours", 72) or 72)

        pipeline_settings = session.query(PipelineSettingsModel).first()
        if pipeline_settings is not None:
            configured_window_hours = int(
                getattr(pipeline_settings, "release_recent_window_hours", configured_window_hours) or configured_window_hours
            )
        configured_window_hours = max(1, configured_window_hours)

        failed_sources: list[dict] = []

        release_articles = discover_recent_releases(
            session,
            now_utc=pipeline_now,
            window_hours=configured_window_hours,
            failed_sources=failed_sources,
        )
        logger.info("Release pipeline discovery complete: count=%s", len(release_articles))

        persisted_articles = _persist_articles(session, release_articles)

        report = _get_or_create_daily_report(session, report_date=datetime.date.today())
        report.releases_pipeline_ran_at = pipeline_now
        report.generated_at = datetime.datetime.utcnow()
        _attach_report_articles(report, persisted_articles)

        session.commit()
        logger.info("Release pipeline complete: discovered=%s saved=%s", len(release_articles), len(persisted_articles))
        return {
            "releases_found": len(release_articles),
            "releases_saved": len(persisted_articles),
            "failed_sources": failed_sources,
            "failed_sources_count": len(failed_sources),
            "release_recent_window_hours": configured_window_hours,
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
    """Start APScheduler daily cron task with configurable time.

    Reads scheduler_hour and scheduler_minute from database PipelineSettings.
    Falls back to environment config if database not ready.

    TODO: Prevent duplicate scheduling in multi-worker deployment.
    """
    if _scheduler.running:
        return

    from app.models import PipelineSettings

    # Try to read from database, fall back to config if unavailable
    scheduler_hour = 7
    scheduler_minute = 0
    scheduler_timezone = "UTC"

    try:
        db = SessionLocal()
        settings = db.query(PipelineSettings).first()
        if settings:
            scheduler_hour = settings.scheduler_hour
            scheduler_minute = settings.scheduler_minute
            scheduler_timezone = settings.scheduler_timezone
        db.close()
    except Exception as e:
        logger.warning(f"Failed to read pipeline settings from DB: {e}. Using defaults.")

    logger.info(
        f"Scheduler configured to run at {scheduler_hour:02d}:{scheduler_minute:02d} {scheduler_timezone}"
    )

    def _safe_add_job(func, job_id: str) -> None:
        try:
            _scheduler.add_job(
                func,
                trigger=CronTrigger(hour=scheduler_hour, minute=scheduler_minute, timezone=scheduler_timezone),
                id=job_id,
                replace_existing=True,
                coalesce=True,
                max_instances=1,
            )
        except TypeError:
            # Compatibility with lightweight test doubles that do not accept APScheduler kwargs.
            _scheduler.add_job(
                func,
                trigger=CronTrigger(hour=scheduler_hour, minute=scheduler_minute, timezone=scheduler_timezone),
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
