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
    tags: Mapped[str | None] = mapped_column(String(512), nullable=True)
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
    generated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    articles: Mapped[list[Article]] = relationship("Article", secondary=report_articles, back_populates="reports")

    def __repr__(self) -> str:
        return f"<Report id={self.id} date={self.report_date} kept={self.total_articles_kept}>"


Index("ix_articles_score", Article.score)
Index("ix_articles_scraped_date", Article.scraped_date)
