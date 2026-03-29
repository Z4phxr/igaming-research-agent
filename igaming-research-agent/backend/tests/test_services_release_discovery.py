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


def test_discover_recent_releases_skips_quarantined_source(monkeypatch):
    db = _build_session()
    try:
        future = datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        db.add(
            ReleaseSource(
                company_name="Quarantined Source",
                category="Regulator",
                source_url="https://q.example.com/news",
                notes="",
                is_active=True,
                quarantine_until=future,
            )
        )
        db.commit()

        called = {"value": False}

        def fake_get(*args, **kwargs):
            called["value"] = True
            return _FakeResponse(200, "<html></html>")

        monkeypatch.setattr(release_discovery.requests, "get", fake_get)
        result = release_discovery.discover_recent_releases(db, now_utc=datetime.datetime.utcnow())

        assert result == []
        assert called["value"] is False
    finally:
        db.close()


def test_discover_recent_releases_applies_local_rate_limit(monkeypatch):
    db = _build_session()
    try:
        db.add_all(
            [
                ReleaseSource(
                    company_name="Source One",
                    category="Operator",
                    source_url="https://same-domain.example.com/news/one",
                    notes="",
                    is_active=True,
                    max_requests_per_hour=1,
                    crawl_delay_seconds=0,
                ),
                ReleaseSource(
                    company_name="Source Two",
                    category="Operator",
                    source_url="https://same-domain.example.com/news/two",
                    notes="",
                    is_active=True,
                    max_requests_per_hour=1,
                    crawl_delay_seconds=0,
                ),
            ]
        )
        db.commit()

        def fake_get(*args, **kwargs):
            return _FakeResponse(200, "<html><a href='/news-releases/2025/11/release-1.html'>r</a></html>")

        monkeypatch.setattr(release_discovery.requests, "get", fake_get)
        monkeypatch.setattr(settings, "release_max_links_per_source", 1)
        monkeypatch.setattr(settings, "release_max_fetches_per_source", 1)
        monkeypatch.setattr(settings, "release_request_jitter_seconds", 0)

        result = release_discovery.discover_recent_releases(db, now_utc=datetime.datetime.utcnow())

        # Article pages are not fetched (missing meta date), but run should complete and enforce source-level limit.
        assert isinstance(result, list)
        sources = db.query(ReleaseSource).order_by(ReleaseSource.id.asc()).all()
        assert sources[0].last_listing_checked_at is not None
        assert sources[1].last_failure_reason == "local_rate_limit"
    finally:
        db.close()


def test_discover_recent_releases_wynn_listing_fallback_url_on_timeout(monkeypatch):
        db = _build_session()
        try:
                db.add(
                        ReleaseSource(
                                company_name="WynnBET",
                                category="Operator",
                                source_url="https://investors.wynnresorts.com/press-releases",
                                notes="",
                                is_active=True,
                                crawl_delay_seconds=0,
                                max_requests_per_hour=100,
                        )
                )
                db.commit()

                calls: list[str] = []
                fallback_listing_html = """
                <table class='table'>
                    <tbody>
                        <tr>
                            <td><time>03/29/26</time></td>
                            <td>
                                <a class='more-item' href='/news-releases/news-release-details/wynn-resorts-issues-update-wynn-al-marjan-island'>
                                    <span class='more-item__text'>Wynn Resorts Issues Update on Wynn Al Marjan Island</span>
                                </a>
                            </td>
                        </tr>
                    </tbody>
                </table>
                """

                def fake_get(url, *args, **kwargs):
                        calls.append(url)
                        if url == "https://investors.wynnresorts.com/press-releases":
                                raise requests.Timeout("primary timeout")
                        if url in {
                                "https://investors.wynnresorts.com/news-releases",
                                "https://investors.wynnresorts.com/news-releases/",
                        }:
                                return _FakeResponse(200, fallback_listing_html)
                        return _FakeResponse(404, "not found")

                monkeypatch.setattr(release_discovery.requests, "get", fake_get)
                monkeypatch.setattr(release_discovery.time, "sleep", lambda _: None)
                monkeypatch.setattr(release_discovery.settings, "release_fetch_max_retries", 0)
                monkeypatch.setattr(release_discovery.settings, "release_max_links_per_source", 5)
                monkeypatch.setattr(release_discovery.settings, "release_max_fetches_per_source", 5)
                monkeypatch.setattr(release_discovery.settings, "release_request_jitter_seconds", 0)

                now = datetime.datetime(2026, 3, 30, 12, 0, 0)
                result = release_discovery.discover_recent_releases(db, now_utc=now)

                assert len(result) == 1
                assert result[0]["url"] == (
                        "https://investors.wynnresorts.com/news-releases/news-release-details/"
                        "wynn-resorts-issues-update-wynn-al-marjan-island"
                )
                assert result[0]["title"] == "Wynn Resorts Issues Update on Wynn Al Marjan Island"
                assert result[0]["published_date"] == datetime.datetime(2026, 3, 29)
                assert "https://investors.wynnresorts.com/press-releases" in calls
                assert "https://investors.wynnresorts.com/news-releases" in calls or "https://investors.wynnresorts.com/news-releases/" in calls
        finally:
                db.close()


def test_discover_recent_releases_kalshi_dedicated_parser_accepts_in_window(monkeypatch):
    db = _build_session()
    try:
        db.add(
            ReleaseSource(
                company_name="Kalshi",
                category="Prediction Markets",
                source_url="https://news.kalshi.com/t/announcements",
                notes="",
                is_active=True,
                crawl_delay_seconds=0,
                max_requests_per_hour=100,
            )
        )
        db.commit()

        now = datetime.datetime(2026, 3, 29, 20, 0, 0)

        listing_html = (
            '{"web_title":"ARK Invest x Kalshi","slug":"ark-invest-kalshi-partnership-prediction-markets-research-risk-management"}'
        )
        article_html = (
            '<html><head><title>ARK Invest x Kalshi</title></head><body>'
            '{"datePublished":"2026-03-29T19:34:11.667Z"}'
            '</body></html>'
        )

        def fake_get(url, *args, **kwargs):
            if url == "https://news.kalshi.com/t/announcements":
                return _FakeResponse(200, listing_html)
            if url.startswith("https://news.kalshi.com/p/"):
                return _FakeResponse(200, article_html)
            return _FakeResponse(404, "not found")

        monkeypatch.setattr(release_discovery.requests, "get", fake_get)
        monkeypatch.setattr(release_discovery.settings, "release_max_links_per_source", 5)
        monkeypatch.setattr(release_discovery.settings, "release_max_fetches_per_source", 5)
        monkeypatch.setattr(release_discovery.settings, "release_recent_window_hours", 24)
        monkeypatch.setattr(release_discovery.settings, "release_request_jitter_seconds", 0)

        result = release_discovery.discover_recent_releases(db, now_utc=now)

        assert len(result) == 1
        assert result[0]["url"] == (
            "https://news.kalshi.com/p/ark-invest-kalshi-partnership-prediction-markets-research-risk-management"
        )
        assert result[0]["title"] == "ARK Invest x Kalshi"
        assert result[0]["published_date"] is not None
    finally:
        db.close()


def test_discover_recent_releases_kalshi_structured_empty_reason_logged(monkeypatch):
    db = _build_session()
    try:
        db.add(
            ReleaseSource(
                company_name="Kalshi",
                category="Prediction Markets",
                source_url="https://news.kalshi.com/t/announcements",
                notes="",
                is_active=True,
            )
        )
        db.commit()

        def fake_get(url, *args, **kwargs):
            if url == "https://news.kalshi.com/t/announcements":
                return _FakeResponse(200, "<html><body>plain listing without structured slug</body></html>")
            return _FakeResponse(404, "not found")

        captured = []

        def fake_log_page_result(**kwargs):
            captured.append(kwargs)

        monkeypatch.setattr(release_discovery.requests, "get", fake_get)
        monkeypatch.setattr(release_discovery, "_log_page_result", fake_log_page_result)

        result = release_discovery.discover_recent_releases(db, now_utc=datetime.datetime(2026, 3, 29, 20, 0, 0))

        assert result == []
        assert any(
            item.get("stage") == "listing" and item.get("reason") == "no_structured_slug_found"
            for item in captured
        )
    finally:
        db.close()


def test_discover_recent_releases_kalshi_stops_after_first_stale_article(monkeypatch):
    db = _build_session()
    try:
        db.add(
            ReleaseSource(
                company_name="Kalshi",
                category="Prediction Markets",
                source_url="https://news.kalshi.com/t/announcements",
                notes="",
                is_active=True,
                crawl_delay_seconds=0,
                max_requests_per_hour=100,
            )
        )
        db.commit()

        now = datetime.datetime(2026, 3, 29, 20, 0, 0)

        listing_html = (
            '{"web_title":"Newest","slug":"newest"}'
            '{"web_title":"Older","slug":"older"}'
            '{"web_title":"ShouldNotBeFetched","slug":"should-not-be-fetched"}'
        )

        urls_fetched = []

        def fake_get(url, *args, **kwargs):
            if url == "https://news.kalshi.com/t/announcements":
                return _FakeResponse(200, listing_html)
            urls_fetched.append(url)
            if url.endswith("/newest"):
                return _FakeResponse(200, '{"datePublished":"2026-03-29T19:34:11.667Z"}')
            if url.endswith("/older"):
                return _FakeResponse(200, '{"datePublished":"2026-03-20T19:34:11.667Z"}')
            if url.endswith("/should-not-be-fetched"):
                return _FakeResponse(200, '{"datePublished":"2026-03-29T18:00:00.000Z"}')
            return _FakeResponse(404, "not found")

        monkeypatch.setattr(release_discovery.requests, "get", fake_get)
        monkeypatch.setattr(release_discovery.settings, "release_recent_window_hours", 72)
        monkeypatch.setattr(release_discovery.settings, "release_max_links_per_source", 10)
        monkeypatch.setattr(release_discovery.settings, "release_max_fetches_per_source", 10)
        monkeypatch.setattr(release_discovery.settings, "release_request_jitter_seconds", 0)

        result = release_discovery.discover_recent_releases(db, now_utc=now)

        assert len(result) == 1
        assert any(url.endswith("/newest") for url in urls_fetched)
        assert any(url.endswith("/older") for url in urls_fetched)
        assert not any(url.endswith("/should-not-be-fetched") for url in urls_fetched)
    finally:
        db.close()


def test_discover_recent_releases_evolution_uses_listing_dates_without_article_fetch(monkeypatch):
    db = _build_session()
    try:
        db.add(
            ReleaseSource(
                company_name="Evolution Gaming",
                category="Supplier",
                source_url="https://www.evolution.com/news",
                notes="",
                is_active=True,
                crawl_delay_seconds=0,
                max_requests_per_hour=100,
            )
        )
        db.commit()

        now = datetime.datetime(2026, 3, 29, 20, 0, 0)

        listing_html = '''
        <a href="https://www.evolution.com/news/evolution-launches-crazy-time-brasil/" class="news-card mb-5 col-12">
            <span class="news-card-date">18/03/26</span>
            <div class="news-card-content mt-4">
                <p class="h4">Evolution launches Crazy Time Brasil</p>
            </div>
        </a>
        <a href="https://www.evolution.com/news/older-release/" class="news-card mb-5 col-12">
            <span class="news-card-date">10/03/26</span>
            <div class="news-card-content mt-4">
                <p class="h4">Older release</p>
            </div>
        </a>
        '''

        call_count = {"listing": 0, "article": 0}

        def fake_get(url, *args, **kwargs):
            if url == "https://www.evolution.com/news":
                call_count["listing"] += 1
                return _FakeResponse(200, listing_html)
            call_count["article"] += 1
            return _FakeResponse(404, "not found")

        monkeypatch.setattr(release_discovery.requests, "get", fake_get)
        monkeypatch.setattr(release_discovery.settings, "release_recent_window_hours", 14 * 24)
        monkeypatch.setattr(release_discovery.settings, "release_max_links_per_source", 10)
        monkeypatch.setattr(release_discovery.settings, "release_max_fetches_per_source", 10)
        monkeypatch.setattr(release_discovery.settings, "release_request_jitter_seconds", 0)

        result = release_discovery.discover_recent_releases(db, now_utc=now)

        assert len(result) == 1
        assert result[0]["url"] == "https://www.evolution.com/news/evolution-launches-crazy-time-brasil/"
        assert result[0]["title"] == "Evolution launches Crazy Time Brasil"
        assert call_count["listing"] == 1
        assert call_count["article"] == 0
    finally:
        db.close()


def test_discover_recent_releases_betmgm_uses_listing_dates_without_article_fetch(monkeypatch):
    db = _build_session()
    try:
        db.add(
            ReleaseSource(
                company_name="BetMGM",
                category="Operator",
                source_url="https://sports.betmgm.com/en/blog",
                notes="",
                is_active=True,
                crawl_delay_seconds=0,
                max_requests_per_hour=100,
            )
        )
        db.commit()

        now = datetime.datetime(2026, 3, 29, 20, 0, 0)

        listing_html = '''
                <div class="section-intro">
                    <h2>Latest Stories</h2>
                </div>
                <div id="sf-posts">
        <div class="news-tile long-news-tile -tag news-tile-392227">
          <h3><a href="https://sports.betmgm.com/en/blog/new-partnership/">New partnership</a></h3>
          <span class="tile-date">Mar 20, 2026</span>
        </div>
        <div class="news-tile long-news-tile -tag news-tile-392228">
          <h3><a href="https://sports.betmgm.com/en/blog/old-news/">Old news</a></h3>
          <span class="tile-date">Jan 20, 2026</span>
        </div>
                </div>
        '''

        call_count = {"listing": 0, "article": 0}

        def fake_get(url, *args, **kwargs):
            if url == "https://sports.betmgm.com/en/blog":
                call_count["listing"] += 1
                return _FakeResponse(200, listing_html)
            call_count["article"] += 1
            return _FakeResponse(404, "not found")

        monkeypatch.setattr(release_discovery.requests, "get", fake_get)
        monkeypatch.setattr(release_discovery.settings, "release_recent_window_hours", 30 * 24)
        monkeypatch.setattr(release_discovery.settings, "release_max_links_per_source", 10)
        monkeypatch.setattr(release_discovery.settings, "release_max_fetches_per_source", 10)
        monkeypatch.setattr(release_discovery.settings, "release_request_jitter_seconds", 0)

        result = release_discovery.discover_recent_releases(db, now_utc=now)

        assert len(result) == 1
        assert result[0]["url"] == "https://sports.betmgm.com/en/blog/new-partnership/"
        assert result[0]["title"] == "New partnership"
        assert call_count["listing"] == 1
        assert call_count["article"] == 0
    finally:
        db.close()
