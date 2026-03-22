"""Report endpoints.

TODO: Add endpoint for report by specific date.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Report as ReportModel
from app.schemas import ReportOut, ReportSummaryOut

router = APIRouter()


@router.get("", response_model=list[ReportSummaryOut])
def list_reports(db: Session = Depends(get_db)):
    return (
        db.query(ReportModel)
        .order_by(ReportModel.report_date.desc())
        .all()
    )


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
