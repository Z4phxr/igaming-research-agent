import datetime

import pytest
from pydantic import ValidationError

from app.schemas import QueryCreate, QueryOut, QueryUpdate, ReportOut


def test_query_create_schema_valid_payload():
    payload = QueryCreate(
        search_term="US betting regulation",
        stream_type="legislative",
        description="Daily tracking",
        is_active=True,
    )

    assert payload.search_term == "US betting regulation"
    assert payload.stream_type == "legislative"


def test_query_create_schema_invalid_stream_type():
    with pytest.raises(ValidationError):
        QueryCreate(
            search_term="Invalid stream",
            stream_type="other",
            is_active=True,
        )


def test_query_update_schema_accepts_partial():
    payload = QueryUpdate(search_term="Updated term")

    assert payload.search_term == "Updated term"
    assert payload.stream_type is None


def test_query_out_schema_serialization():
    now = datetime.datetime.utcnow()
    payload = QueryOut(
        id=1,
        search_term="US iGaming",
        stream_type="business",
        description=None,
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    assert payload.id == 1
    assert payload.model_dump()["stream_type"] == "business"


def test_report_out_schema_with_articles():
    now = datetime.datetime.utcnow()
    report = ReportOut(
        id=1,
        report_date=datetime.date.today(),
        total_articles_found=2,
        total_articles_kept=1,
        generated_at=now,
        articles=[
            {
                "id": 10,
                "title": "Story",
                "url": "https://example.com/story",
                "source_domain": "example.com",
                "summary": "Brief",
                "full_text": "Body",
                "score": 7,
                "tags": "market",
                "matched_query_id": 2,
                "published_date": now,
                "scraped_date": now,
                "created_at": now,
            }
        ],
    )

    assert report.articles[0].title == "Story"
