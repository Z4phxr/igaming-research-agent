"""CRUD endpoints for query management.

TODO: Add pagination/filtering by stream type for large query sets.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Query as QueryModel
from app.schemas import QueryCreate, QueryOut, QueryUpdate

router = APIRouter()


@router.get("", response_model=list[QueryOut])
def list_queries(db: Session = Depends(get_db)):
    return db.query(QueryModel).order_by(QueryModel.id.asc()).all()


@router.post("", response_model=QueryOut, status_code=status.HTTP_201_CREATED)
def create_query(payload: QueryCreate, db: Session = Depends(get_db)):
    item = QueryModel(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{query_id}", response_model=QueryOut)
def update_query(query_id: int, payload: QueryUpdate, db: Session = Depends(get_db)):
    item = db.get(QueryModel, query_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Query not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{query_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_query(query_id: int, db: Session = Depends(get_db)):
    item = db.get(QueryModel, query_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Query not found")
    db.delete(item)
    db.commit()
