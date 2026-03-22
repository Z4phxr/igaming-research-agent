"""Database setup for SQLAlchemy + SQLite.

SQLite file is stored at backend/data.db.
TODO: Replace with Alembic migrations in production.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args, echo=False)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


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
