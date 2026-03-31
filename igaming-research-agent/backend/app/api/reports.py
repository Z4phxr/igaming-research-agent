"""Report endpoints.

TODO: Add endpoint for report by specific date.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Article as ArticleModel
from app.models import ArticleFeedback as ArticleFeedbackModel
from app.models import Report as ReportModel
from app.schemas import ArticleFeedbackCreate, ReportSummaryOut
from app.services.analyzer import build_rejection_metadata
from app.services.scheduler import run_articles_pipeline, run_daily_pipeline, run_release_pipeline

router = APIRouter()
feedback_router = APIRouter()


def _serialize_report(report: ReportModel, show_all: bool, show_all_info: bool, db: Session) -> dict:
    top_story_articles = [
        article
        for article in report.articles
        if getattr(article, "article_type", "top_story") != "release"
    ]
    filtered_articles = [
        article for article in top_story_articles if show_all or bool(getattr(article, "kept", True))
    ]
    release_articles = [
        article
        for article in report.articles
        if getattr(article, "article_type", "top_story") == "release"
    ]
    release_articles.sort(
        key=lambda article: article.published_date or article.scraped_date,
        reverse=True,
    )

    def _serialize_article(article: ArticleModel) -> dict:
        payload = {
            "id": article.id,
            "title": article.title,
            "url": article.url,
            "source_domain": article.source_domain,
            "summary": article.summary,
            "full_text": article.full_text,
            "score": article.score,
            "raw_score": article.raw_score,
            "passed_relevance_filter": article.passed_relevance_filter,
            "kept": article.kept,
            "rejection_reason": article.rejection_reason,
            "tags": article.tags,
            "article_type": getattr(article, "article_type", "top_story"),
            "matched_query_id": article.matched_query_id,
            "published_date": article.published_date,
            "scraped_date": article.scraped_date,
            "created_at": article.created_at,
        }

        if not bool(article.kept):
            payload.update(build_rejection_metadata(payload, include_llm_why=show_all_info, db=db))

        return payload

    return {
        "id": report.id,
        "report_date": report.report_date,
        "total_articles_found": report.total_articles_found,
        "total_articles_kept": report.total_articles_kept,
        "briefing": report.briefing,
        "briefing_generated_at": report.briefing_generated_at,
        "generated_at": report.generated_at,
        "articles": [_serialize_article(article) for article in filtered_articles],
        "release_articles": [_serialize_article(article) for article in release_articles],
    }


@router.get("", response_model=list[ReportSummaryOut])
def list_reports(db: Session = Depends(get_db)):
    return (
        db.query(ReportModel)
        .order_by(ReportModel.report_date.desc())
        .all()
    )


@router.post("/run")
def run_reports_pipeline(db: Session = Depends(get_db)):
    count_before = db.query(ReportModel).count()

    try:
        run_daily_pipeline(db, raise_on_error=True)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(exc)},
        )

    db.expire_all()
    latest_after = (
        db.query(ReportModel)
        .order_by(ReportModel.generated_at.desc(), ReportModel.id.desc())
        .first()
    )
    count_after = db.query(ReportModel).count()

    if latest_after is None:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Pipeline completed without creating a report"},
        )

    if count_after <= count_before:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Pipeline did not create a new report"},
        )

    articles_found = int(latest_after.total_articles_found or 0)
    if articles_found == 0:
        return {
            "status": "success",
            "message": "Pipeline ran but found no articles",
            "articles_found": 0,
        }

    return {
        "status": "success",
        "message": "Pipeline completed",
        "articles_found": articles_found,
    }


@router.post("/run/articles")
def run_articles_only_pipeline(db: Session = Depends(get_db)):
    try:
        result = run_articles_pipeline(db, raise_on_error=True)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(exc)},
        )

    articles_found = int(result.get("articles_found", 0) or 0)
    if articles_found == 0:
        return {
            "status": "success",
            "message": "Articles pipeline ran but found no articles",
            "articles_found": 0,
        }

    return {
        "status": "success",
        "message": "Articles pipeline completed",
        "articles_found": articles_found,
    }


@router.post("/run/releases")
def run_releases_only_pipeline(db: Session = Depends(get_db)):
    try:
        result = run_release_pipeline(db, raise_on_error=True)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(exc)},
        )

    releases_found = int(result.get("releases_found", 0) or 0)
    if releases_found == 0:
        return {
            "status": "success",
            "message": "Releases pipeline ran but found no releases",
            "releases_found": 0,
        }

    return {
        "status": "success",
        "message": "Releases pipeline completed",
        "releases_found": releases_found,
    }


@router.get("/latest")
def get_latest_report(show_all: bool = False, show_all_info: bool = False, db: Session = Depends(get_db)):
    report = (
        db.query(ReportModel)
        .options(selectinload(ReportModel.articles))
        .order_by(ReportModel.report_date.desc(), ReportModel.id.desc())
        .first()
    )
    if report is None:
        raise HTTPException(status_code=404, detail="No reports found")
    return _serialize_report(report, show_all=show_all, show_all_info=show_all_info, db=db)


@router.get("/{report_id}")
def get_report(report_id: int, show_all: bool = False, show_all_info: bool = False, db: Session = Depends(get_db)):
    report = (
        db.query(ReportModel)
        .options(selectinload(ReportModel.articles))
        .filter(ReportModel.id == report_id)
        .first()
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return _serialize_report(report, show_all=show_all, show_all_info=show_all_info, db=db)


@feedback_router.post("/articles/{article_id}/feedback")
def submit_article_feedback(
    article_id: int,
    payload: ArticleFeedbackCreate,
    db: Session = Depends(get_db),
):
    article = db.query(ArticleModel).filter(ArticleModel.id == article_id).first()
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")

    corrected_score = payload.user_corrected_score
    if corrected_score is not None and not 1 <= corrected_score <= 10:
        raise HTTPException(status_code=400, detail="user_corrected_score must be between 1 and 10")

    if payload.feedback_type in {"score_too_low", "score_too_high"} and corrected_score is None:
        raise HTTPException(status_code=400, detail="user_corrected_score is required for score feedback")

    if payload.feedback_type == "helpful":
        corrected_score = None

    feedback = ArticleFeedbackModel(
        article_id=article_id,
        feedback_type=payload.feedback_type,
        user_corrected_score=corrected_score,
    )
    db.add(feedback)
    db.commit()

    return {"status": "success", "message": "Thank you for the feedback"}
