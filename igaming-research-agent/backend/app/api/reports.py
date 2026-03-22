"""Report endpoints.

TODO: Add endpoint for report by specific date.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Report as ReportModel
from app.schemas import ReportOut, ReportSummaryOut
from app.services.scheduler import run_daily_pipeline

router = APIRouter()


@router.get("", response_model=list[ReportSummaryOut])
def list_reports(db: Session = Depends(get_db)):
    return (
        db.query(ReportModel)
        .order_by(ReportModel.report_date.desc())
        .all()
    )


@router.post("/run")
def run_reports_pipeline(db: Session = Depends(get_db)):
    latest_before = (
        db.query(ReportModel)
        .order_by(ReportModel.generated_at.desc(), ReportModel.id.desc())
        .first()
    )

    try:
        run_daily_pipeline(db)
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

    if latest_after is None:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Pipeline completed without creating a report"},
        )

    if latest_before is not None and latest_before.id == latest_after.id:
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


@router.get("/latest", response_model=ReportOut)
def get_latest_report(db: Session = Depends(get_db)):
    report = (
        db.query(ReportModel)
        .options(selectinload(ReportModel.articles))
        .order_by(ReportModel.report_date.desc(), ReportModel.id.desc())
        .first()
    )
    if report is None:
        raise HTTPException(status_code=404, detail="No reports found")
    return report


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = (
        db.query(ReportModel)
        .options(selectinload(ReportModel.articles))
        .filter(ReportModel.id == report_id)
        .first()
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
