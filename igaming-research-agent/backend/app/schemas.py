"""Pydantic schemas for API request/response payloads.

TODO: Add stricter field validators and custom error messages.
"""

import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class QueryBase(BaseModel):
    search_term: str = Field(..., min_length=1, max_length=1024)
    stream_type: str = Field(..., pattern="^(legislative|business|whitelist)$")
    description: Optional[str] = None
    is_active: bool = True


class QueryCreate(QueryBase):
    """Create query payload."""


class QueryUpdate(BaseModel):
    search_term: Optional[str] = Field(None, min_length=1, max_length=1024)
    stream_type: Optional[str] = Field(None, pattern="^(legislative|business|whitelist)$")
    description: Optional[str] = None
    is_active: Optional[bool] = None


class QueryOut(QueryBase):
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class ArticleOut(BaseModel):
    id: int
    title: str
    url: str
    source_domain: Optional[str] = None
    summary: Optional[str] = None
    full_text: Optional[str] = None
    score: Optional[int] = None
    tags: Optional[str] = None
    matched_query_id: Optional[int] = None
    published_date: Optional[datetime.datetime] = None
    scraped_date: datetime.datetime
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class ReportSummaryOut(BaseModel):
    id: int
    report_date: datetime.date
    total_articles_found: Optional[int] = None
    total_articles_kept: Optional[int] = None
    generated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class ReportOut(ReportSummaryOut):
    articles: list[ArticleOut] = []
