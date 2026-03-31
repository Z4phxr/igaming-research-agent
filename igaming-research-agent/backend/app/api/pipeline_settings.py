"""CRUD endpoints for pipeline configuration settings.

TODO: Add role-based access control for settings updates.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PipelineSettings as PipelineSettingsModel
from app.schemas import PipelineSettingsOut, PipelineSettingsUpdate

router = APIRouter()


def _ensure_settings_exist(db: Session) -> PipelineSettingsModel:
    """Ensure a settings row exists; create with defaults if missing."""
    settings = db.query(PipelineSettingsModel).first()
    if not settings:
        settings = PipelineSettingsModel(
            scheduler_hour=7,
            scheduler_minute=0,
            scheduler_timezone="UTC",
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("", response_model=PipelineSettingsOut)
def get_pipeline_settings(db: Session = Depends(get_db)):
    """Get current pipeline settings."""
    settings = _ensure_settings_exist(db)
    return settings


@router.put("", response_model=PipelineSettingsOut)
def update_pipeline_settings(
    payload: PipelineSettingsUpdate,
    db: Session = Depends(get_db),
):
    """Update pipeline settings (scheduler time, timezone, etc.)."""
    settings = _ensure_settings_exist(db)

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(settings, key, value)

    db.commit()
    db.refresh(settings)

    # Log the update for debugging
    import logging

    logger = logging.getLogger(__name__)
    logger.info(
        f"Pipeline settings updated: {settings.scheduler_hour:02d}:{settings.scheduler_minute:02d} {settings.scheduler_timezone}"
    )

    # TODO: Restart scheduler gracefully with new time
    # For now, admin needs to restart the app for changes to take effect

    return settings


