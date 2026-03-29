"""CRUD endpoints for release source management."""

import datetime
import logging
from typing import Any
from urllib.parse import urljoin

import requests

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import ReleaseSource as ReleaseSourceModel
from app.schemas import ReleaseSourceCreate, ReleaseSourceOut, ReleaseSourceUpdate
from app.services.portal_scrapers import resolve_listing_parser
from app.services.release_discovery import (
    _extract_hrefs,
    _extract_published_date,
    _extract_title,
    _is_same_site,
    _is_valid_candidate_href,
    _looks_like_release_link,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _http_get(url: str, timeout: int = 20) -> str:
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": settings.release_fetch_user_agent},
    )
    response.raise_for_status()
    return response.text


def _run_single_source_health_check(source: ReleaseSourceModel, now_utc: datetime.datetime) -> dict[str, Any]:
    parser = resolve_listing_parser(source.source_url, source.company_name)
    base_result: dict[str, Any] = {
        "source_id": source.id,
        "company_name": source.company_name,
        "source_url": source.source_url,
        "passed": False,
        "latest_article_url": None,
        "latest_article_title": None,
        "latest_article_published_at": None,
        "latest_article_age_hours": None,
        "error_log": None,
        "checked_at": now_utc.isoformat(),
    }

    try:
        listing_html = _http_get(source.source_url)
    except requests.RequestException as exc:
        base_result["error_log"] = f"Listing fetch failed: {exc}"
        return base_result

    if parser is not None:
        parsed = parser.parse_listing(
            listing_html=listing_html,
            source_url=source.source_url,
            company_name=source.company_name,
            cutoff=None,
            now_utc=now_utc,
        )
        candidate_urls = parsed.candidate_urls
        candidate_titles = parsed.candidate_titles
        candidate_dates = parsed.candidate_published_dates
        empty_reason = parsed.empty_reason
    else:
        candidate_urls: list[str] = []
        candidate_titles: dict[str, str] = {}
        candidate_dates: dict[str, datetime.datetime] = {}
        seen: set[str] = set()

        for href in _extract_hrefs(listing_html):
            if not _is_valid_candidate_href(href):
                continue

            absolute_url = urljoin(source.source_url, href)
            if absolute_url in seen:
                continue
            if not _looks_like_release_link(absolute_url):
                continue
            if not _is_same_site(source.source_url, absolute_url):
                continue

            seen.add(absolute_url)
            candidate_urls.append(absolute_url)

        empty_reason = "no_candidate_links_generic_fallback"

    if not candidate_urls:
        reason = empty_reason or "no_candidate_urls"
        base_result["error_log"] = f"No candidates found: {reason}"
        return base_result

    newest_url = candidate_urls[0]
    newest_title = candidate_titles.get(newest_url)
    newest_published = candidate_dates.get(newest_url)

    # Probe a few top candidates and keep the newest published timestamp when available.
    for candidate_url in candidate_urls[:5]:
        candidate_title = candidate_titles.get(candidate_url)
        candidate_published = candidate_dates.get(candidate_url)

        if candidate_published is None:
            try:
                article_html = _http_get(candidate_url)
            except requests.RequestException:
                continue

            if parser is not None:
                candidate_published = parser.extract_article_published_date(article_html)
            if candidate_published is None:
                candidate_published = _extract_published_date(article_html)
            if not candidate_title:
                candidate_title = _extract_title(article_html, fallback=source.company_name)

        if candidate_published is not None and (newest_published is None or candidate_published > newest_published):
            newest_published = candidate_published
            newest_url = candidate_url
            newest_title = candidate_title

    base_result["passed"] = True
    base_result["latest_article_url"] = newest_url
    base_result["latest_article_title"] = newest_title or source.company_name

    if newest_published is not None:
        base_result["latest_article_published_at"] = newest_published.isoformat()
        age_seconds = (now_utc - newest_published).total_seconds()
        base_result["latest_article_age_hours"] = max(0, round(age_seconds / 3600, 2))

    return base_result


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


@router.post("/health-check")
def run_release_source_health_check(db: Session = Depends(get_db)):
    now_utc = datetime.datetime.utcnow()
    active_sources = (
        db.query(ReleaseSourceModel)
        .filter(ReleaseSourceModel.is_active == True)  # noqa: E712
        .order_by(ReleaseSourceModel.company_name.asc(), ReleaseSourceModel.id.asc())
        .all()
    )

    results = [_run_single_source_health_check(source, now_utc=now_utc) for source in active_sources]
    passed_count = sum(1 for item in results if item["passed"])

    return {
        "status": "success",
        "checked_at": now_utc.isoformat(),
        "total_sources": len(results),
        "passed_sources": passed_count,
        "failed_sources": len(results) - passed_count,
        "results": results,
    }


@router.post("/health-check/{source_id}")
def run_single_release_source_health_check(source_id: int, db: Session = Depends(get_db)):
    source = db.get(ReleaseSourceModel, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Release source not found")

    now_utc = datetime.datetime.utcnow()
    result = _run_single_source_health_check(source, now_utc=now_utc)
    return {
        "status": "success",
        "checked_at": now_utc.isoformat(),
        "result": result,
    }
