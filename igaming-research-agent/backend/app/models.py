"""SQLAlchemy models: Query, Article, Report.

TODO: Add richer constraints/checks (e.g., score range at DB level).
"""

import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


report_articles = Table(
    "report_articles",
    Base.metadata,
    Column("report_id", Integer, ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True),
    Column("article_id", Integer, ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True),
)


class Query(Base):
    """Saved search query formula used by daily search.

    TODO: Enforce stream_type enum at validation layer and/or DB check constraint.
    """

    __tablename__ = "queries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    search_term: Mapped[str] = mapped_column(String(1024), nullable=False)
    stream_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=False,
    )

    articles: Mapped[list["Article"]] = relationship("Article", back_populates="matched_query")

    def __repr__(self) -> str:
        return f"<Query id={self.id} stream={self.stream_type} active={self.is_active}>"


class Article(Base):
    """Scraped article record with LLM metadata.

    TODO: Normalize tags into a separate table when taxonomy expands.
    """

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False, index=True)
    source_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passed_relevance_filter: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    kept: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tags: Mapped[str | None] = mapped_column(String(512), nullable=True)
    article_type: Mapped[str] = mapped_column(String(32), default="top_story", nullable=False, index=True)
    matched_query_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("queries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    published_date: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    scraped_date: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    matched_query: Mapped[Query | None] = relationship("Query", back_populates="articles")
    reports: Mapped[list["Report"]] = relationship("Report", secondary=report_articles, back_populates="articles")
    feedback_entries: Mapped[list["ArticleFeedback"]] = relationship(
        "ArticleFeedback",
        back_populates="article",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Article id={self.id} score={self.score} title='{self.title[:40]}'>"


class Report(Base):
    """Daily report containing top selected articles.

    TODO: Add run metadata (duration, error_count, source_count).
    """

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    total_articles_found: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_articles_kept: Mapped[int | None] = mapped_column(Integer, nullable=True)
    briefing: Mapped[str | None] = mapped_column(Text, nullable=True)
    briefing_generated_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    generated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    articles: Mapped[list[Article]] = relationship("Article", secondary=report_articles, back_populates="reports")

    def __repr__(self) -> str:
        return f"<Report id={self.id} date={self.report_date} kept={self.total_articles_kept}>"


class ArticleFeedback(Base):
    """User feedback on article quality/scoring for future model training."""

    __tablename__ = "article_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    feedback_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    user_corrected_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    article: Mapped[Article] = relationship("Article", back_populates="feedback_entries")


class ReleaseSource(Base):
    """Configured company/news source pages for release discovery."""

    __tablename__ = "release_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source_tier: Mapped[int] = mapped_column(Integer, default=3, nullable=False, index=True)
    preferred_method: Mapped[str] = mapped_column(String(32), default="auto", nullable=False)
    crawl_delay_seconds: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    max_requests_per_hour: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    health_score: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    quarantine_until: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    last_failure_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_success_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    last_listing_etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_listing_modified: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_listing_checked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=False,
    )


class PromptTemplate(Base):
    """Editable prompt template with active published version metadata."""

    __tablename__ = "prompt_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    draft_content: Mapped[str] = mapped_column(Text, nullable=False)
    active_content: Mapped[str] = mapped_column(Text, nullable=False)
    active_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=False,
    )

    versions: Mapped[list["PromptTemplateVersion"]] = relationship(
        "PromptTemplateVersion",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="PromptTemplateVersion.version.desc()",
    )


class PromptTemplateVersion(Base):
    """Version history for prompt template publishes."""

    __tablename__ = "prompt_template_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prompt_template_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("prompt_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    template: Mapped[PromptTemplate] = relationship("PromptTemplate", back_populates="versions")


Index("ix_articles_score", Article.score)
Index("ix_articles_scraped_date", Article.scraped_date)
Index("ix_release_sources_company_name", ReleaseSource.company_name)
Index("ix_prompt_template_version_unique", PromptTemplateVersion.prompt_template_id, PromptTemplateVersion.version, unique=True)
