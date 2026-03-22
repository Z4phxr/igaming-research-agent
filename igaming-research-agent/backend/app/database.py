"""Database setup for SQLAlchemy connection/session management.

TODO: Replace metadata create_all with migration-based schema management.
"""

import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency for DB session.

    TODO: Add request-level tracing metadata to sessions if needed.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all registered tables.

    TODO: Switch to migration-based schema management.
    """
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    ensure_article_runtime_columns()


def ensure_article_runtime_columns() -> None:
    """Backfill newer Article columns in existing databases without migrations."""
    inspector = inspect(engine)
    if "articles" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("articles")}
    dialect = engine.dialect.name
    bool_default = "1" if dialect == "sqlite" else "TRUE"

    statements: list[str] = []
    if "raw_score" not in existing_columns:
        statements.append("ALTER TABLE articles ADD COLUMN raw_score INTEGER")
    if "passed_relevance_filter" not in existing_columns:
        statements.append(
            f"ALTER TABLE articles ADD COLUMN passed_relevance_filter BOOLEAN NOT NULL DEFAULT {bool_default}"
        )
    if "kept" not in existing_columns:
        statements.append(f"ALTER TABLE articles ADD COLUMN kept BOOLEAN NOT NULL DEFAULT {bool_default}")
    if "rejection_reason" not in existing_columns:
        statements.append("ALTER TABLE articles ADD COLUMN rejection_reason VARCHAR(64)")

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
