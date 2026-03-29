"""CRUD endpoints for release source management."""

import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ReleaseSource as ReleaseSourceModel
from app.schemas import ReleaseSourceCreate, ReleaseSourceOut, ReleaseSourceUpdate

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("")
def list_release_sources(db: Session = Depends(get_db)):
    try:
        rows = db.query(ReleaseSourceModel).order_by(ReleaseSourceModel.id.asc()).all()
        now = datetime.datetime.utcnow()
        payload = [
            {
                "id": row.id,
                "company_name": row.company_name or "",
                "category": row.category or "",
                "source_url": row.source_url or "",
                "notes": row.notes or "",
                "source_tier": int(getattr(row, "source_tier", 3) or 3),
                "preferred_method": str(getattr(row, "preferred_method", "auto") or "auto"),
                "crawl_delay_seconds": int(getattr(row, "crawl_delay_seconds", 2) or 2),
                "max_requests_per_hour": int(getattr(row, "max_requests_per_hour", 60) or 60),
                "consecutive_failures": int(getattr(row, "consecutive_failures", 0) or 0),
                "health_score": int(getattr(row, "health_score", 100) or 100),
                "quarantine_until": getattr(row, "quarantine_until", None).isoformat()
                if getattr(row, "quarantine_until", None)
                else None,
                "last_failure_reason": getattr(row, "last_failure_reason", None),
                "last_success_at": getattr(row, "last_success_at", None).isoformat()
                if getattr(row, "last_success_at", None)
                else None,
                "last_listing_checked_at": getattr(row, "last_listing_checked_at", None).isoformat()
                if getattr(row, "last_listing_checked_at", None)
                else None,
                "is_active": bool(row.is_active),
                "created_at": (row.created_at or now).isoformat(),
                "updated_at": (row.updated_at or now).isoformat(),
            }
            for row in rows
        ]
        return JSONResponse(content=payload)
    except Exception:
        logger.exception("Failed to list release sources")
        return JSONResponse(content=[])


@router.post("", response_model=ReleaseSourceOut, status_code=status.HTTP_201_CREATED)
def create_release_source(payload: ReleaseSourceCreate, db: Session = Depends(get_db)):
    normalized_url = payload.source_url.strip()
    existing = db.query(ReleaseSourceModel).filter(ReleaseSourceModel.source_url == normalized_url).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Release source already exists")

    data = payload.model_dump()
    data["source_url"] = normalized_url
    item = ReleaseSourceModel(**data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{source_id}", response_model=ReleaseSourceOut)
def update_release_source(source_id: int, payload: ReleaseSourceUpdate, db: Session = Depends(get_db)):
    item = db.get(ReleaseSourceModel, source_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Release source not found")

    updates = payload.model_dump(exclude_unset=True)
    if "source_url" in updates:
        updates["source_url"] = str(updates["source_url"]).strip()
        duplicate = (
            db.query(ReleaseSourceModel)
            .filter(ReleaseSourceModel.source_url == updates["source_url"], ReleaseSourceModel.id != source_id)
            .first()
        )
        if duplicate is not None:
            raise HTTPException(status_code=409, detail="Release source already exists")

    for key, value in updates.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_release_source(source_id: int, db: Session = Depends(get_db)):
    item = db.get(ReleaseSourceModel, source_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Release source not found")
    db.delete(item)
    db.commit()
