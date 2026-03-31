"""Pydantic schemas for API request/response payloads.

TODO: Add stricter field validators and custom error messages.
"""

import datetime
from typing import Literal, Optional

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
    article_type: str = "top_story"
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
    briefing: Optional[str] = None
    briefing_generated_at: Optional[datetime.datetime] = None
    articles_pipeline_ran_at: Optional[datetime.datetime] = None
    releases_pipeline_ran_at: Optional[datetime.datetime] = None
    generated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class ReportOut(ReportSummaryOut):
    articles: list[ArticleOut] = []


class ArticleFeedbackCreate(BaseModel):
    feedback_type: Literal["helpful", "score_too_low", "score_too_high"]
    user_corrected_score: Optional[int] = None


class ArticleFeedbackOut(BaseModel):
    id: int
    article_id: int
    feedback_type: Literal["helpful", "score_too_low", "score_too_high"]
    user_corrected_score: Optional[int] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class ReleaseSourceBase(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=64)
    source_url: str = Field(..., min_length=1, max_length=2048)
    notes: Optional[str] = Field(None, max_length=1024)
    source_tier: int = Field(default=3, ge=1, le=4)
    preferred_method: str = Field(default="auto", min_length=1, max_length=32)
    crawl_delay_seconds: int = Field(default=2, ge=0, le=3600)
    max_requests_per_hour: int = Field(default=60, ge=1, le=10000)
    is_active: bool = True


class ReleaseSourceCreate(ReleaseSourceBase):
    """Create release source payload."""


class ReleaseSourceUpdate(BaseModel):
    company_name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, min_length=1, max_length=64)
    source_url: Optional[str] = Field(None, min_length=1, max_length=2048)
    notes: Optional[str] = Field(None, max_length=1024)
    source_tier: Optional[int] = Field(None, ge=1, le=4)
    preferred_method: Optional[str] = Field(None, min_length=1, max_length=32)
    crawl_delay_seconds: Optional[int] = Field(None, ge=0, le=3600)
    max_requests_per_hour: Optional[int] = Field(None, ge=1, le=10000)
    consecutive_failures: Optional[int] = Field(None, ge=0)
    health_score: Optional[int] = Field(None, ge=0, le=100)
    quarantine_until: Optional[datetime.datetime] = None
    last_failure_reason: Optional[str] = Field(None, max_length=64)
    is_active: Optional[bool] = None


class ReleaseSourceOut(ReleaseSourceBase):
    id: int
    consecutive_failures: int = 0
    health_score: int = 100
    quarantine_until: Optional[datetime.datetime] = None
    last_failure_reason: Optional[str] = None
    last_success_at: Optional[datetime.datetime] = None
    last_listing_checked_at: Optional[datetime.datetime] = None
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PromptTemplateVersionOut(BaseModel):
    id: int
    version: int
    content: str
    is_active: bool
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class PromptTemplateOut(BaseModel):
    id: int
    key: str
    title: str
    description: Optional[str] = None
    draft_content: str
    active_content: str
    active_version: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class PromptTemplateDetailOut(PromptTemplateOut):
    history: list[PromptTemplateVersionOut] = []


class PromptTemplateDraftUpdate(BaseModel):
    draft_content: str = Field(..., min_length=1)


class PromptTemplatePublishRequest(BaseModel):
    content: Optional[str] = Field(default=None, min_length=1)


class PipelineSettingsUpdate(BaseModel):
    scheduler_hour: int = Field(..., ge=0, le=23)
    scheduler_minute: int = Field(..., ge=0, le=59)
    scheduler_timezone: str = Field(default="UTC", min_length=1, max_length=32)
    release_recent_window_hours: int = Field(default=72, ge=1, le=24 * 30)


class PipelineSettingsOut(PipelineSettingsUpdate):
    id: int
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class PipelineReevaluateOut(BaseModel):
    status: str
    message: str
    report_id: int
    processed_articles: int
    updated_articles: int
    kept_articles: int


class LlmHealthOut(BaseModel):
    status: str
    provider: str
    model: str
    message: str
    error_code: Optional[str] = None
