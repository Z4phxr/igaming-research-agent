"""CRUD endpoints for release source management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ReleaseSource as ReleaseSourceModel
from app.schemas import ReleaseSourceCreate, ReleaseSourceOut, ReleaseSourceUpdate

router = APIRouter()


@router.get("", response_model=list[ReleaseSourceOut])
def list_release_sources(db: Session = Depends(get_db)):
    return db.query(ReleaseSourceModel).order_by(ReleaseSourceModel.id.asc()).all()


@router.post("", response_model=ReleaseSourceOut, status_code=status.HTTP_201_CREATED)
def create_release_source(payload: ReleaseSourceCreate, db: Session = Depends(get_db)):
    existing = db.query(ReleaseSourceModel).filter(ReleaseSourceModel.source_url == payload.source_url).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Release source already exists")

    item = ReleaseSourceModel(**payload.model_dump())
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
