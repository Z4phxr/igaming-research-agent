import datetime

import pytest
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base
from app.models import ReleaseSource
from app.services import release_discovery


class _FakeResponse:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error", response=self)


def _build_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return session_local()


def test_fetch_html_retries_timeout_then_succeeds(monkeypatch):
    calls = {"count": 0}

    def fake_get(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise requests.Timeout("timed out")
        return _FakeResponse(200, "<html>ok</html>")

    monkeypatch.setattr(release_discovery.requests, "get", fake_get)
    monkeypatch.setattr(release_discovery.time, "sleep", lambda _: None)

    html, meta = release_discovery._fetch_html(
        "https://example.com/news",
        source_name="Example",
        stage="listing_fetch",
        timeout=1,
        max_retries=1,
    )

    assert html == "<html>ok</html>"
    assert meta["ok"] is True
    assert meta["retries_used"] == 1
    assert calls["count"] == 2


def test_fetch_html_does_not_retry_404(monkeypatch):
    calls = {"count": 0}

    def fake_get(*args, **kwargs):
        calls["count"] += 1
        return _FakeResponse(404, "not found")

    monkeypatch.setattr(release_discovery.requests, "get", fake_get)
    monkeypatch.setattr(release_discovery.time, "sleep", lambda _: None)

    html, meta = release_discovery._fetch_html(
        "https://example.com/missing",
        source_name="Example",
        stage="article_fetch",
        timeout=1,
        max_retries=3,
    )

    assert html is None
    assert meta["ok"] is False
    assert meta["error_kind"] == "http_404"
    assert calls["count"] == 1


def test_discover_recent_releases_source_timeout_is_non_fatal(monkeypatch):
    db = _build_session()
    try:
        db.add(
            ReleaseSource(
                company_name="Timeout Source",
                category="Operator",
                source_url="https://timeout.example.com/news",
                notes="",
                is_active=True,
            )
        )
        db.commit()

        monkeypatch.setattr(release_discovery.requests, "get", lambda *args, **kwargs: (_ for _ in ()).throw(requests.Timeout("boom")))
        monkeypatch.setattr(release_discovery.time, "sleep", lambda _: None)
        monkeypatch.setattr(settings, "release_fetch_max_retries", 0)

        result = release_discovery.discover_recent_releases(db, now_utc=datetime.datetime.utcnow())

        assert result == []
    finally:
        db.close()
