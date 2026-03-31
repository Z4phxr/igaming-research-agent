import datetime


def test_release_source_crud_flow(client):
    created = client.post(
        "/api/release-sources",
        json={
            "company_name": "IGT",
            "category": "Slot provider",
            "source_url": "https://www.igt.com/explore-igt/news/news",
            "notes": "Test notes",
            "is_active": True,
        },
    )

    assert created.status_code == 201
    body = created.json()
    assert body["company_name"] == "IGT"
    assert body["category"] == "Slot provider"
    assert body["notes"] == "Test notes"
    assert body["is_active"] is True

    listing = client.get("/api/release-sources")
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    source_id = body["id"]
    updated = client.put(f"/api/release-sources/{source_id}", json={"is_active": False})
    assert updated.status_code == 200
    assert updated.json()["is_active"] is False

    deleted = client.delete(f"/api/release-sources/{source_id}")
    assert deleted.status_code == 204

    listing_after = client.get("/api/release-sources")
    assert listing_after.status_code == 200
    assert listing_after.json() == []


def test_release_source_rejects_duplicates(client):
    payload = {
        "company_name": "IGT",
        "category": "Slot provider",
        "source_url": "https://www.igt.com/explore-igt/news/news",
        "notes": "Test notes",
        "is_active": True,
    }

    first = client.post("/api/release-sources", json=payload)
    second = client.post("/api/release-sources", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "Release source already exists"


def test_release_source_bulk_create_normalizes_urls_and_skips_duplicates(client):
    response = client.post(
        "/api/release-sources/bulk",
        json=[
            {
                "company_name": "DraftKings",
                "category": "Operator",
                "source_url": "www.draftkings.com/news-about",
                "notes": "",
                "is_active": True,
            },
            {
                "company_name": "DraftKings Duplicate",
                "category": "Operator",
                "source_url": "https://www.draftkings.com/news-about",
                "notes": "",
                "is_active": True,
            },
            {
                "company_name": "Hard Rock Bet",
                "category": "Operator",
                "source_url": "https://www.hardrock.com/blog",
                "notes": "",
                "is_active": True,
            },
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["created_count"] == 2
    assert body["skipped_count"] == 1
    assert any(item["source_url"] == "https://www.draftkings.com/news-about" for item in body["created"])
    assert any(item["reason"] == "duplicate_in_payload" for item in body["skipped"])

    listing = client.get("/api/release-sources")
    assert listing.status_code == 200
    assert len(listing.json()) == 2


def test_release_source_health_check_returns_passed_source(client, monkeypatch):
    created = client.post(
        "/api/release-sources",
        json={
            "company_name": "Kalshi",
            "category": "Prediction Market",
            "source_url": "https://news.kalshi.com/t/announcements",
            "notes": "",
            "is_active": True,
        },
    )
    assert created.status_code == 201

    class _Parser:
        def parse_listing(self, **kwargs):
            class _Parsed:
                candidate_urls = ["https://news.kalshi.com/p/latest"]
                candidate_titles = {"https://news.kalshi.com/p/latest": "Latest release"}
                candidate_published_dates = {"https://news.kalshi.com/p/latest": datetime.datetime(2026, 3, 29, 12, 0, 0)}
                empty_reason = None

            return _Parsed()

        def extract_article_published_date(self, _: str):
            return datetime.datetime(2026, 3, 29, 12, 0, 0)

    from app.api import release_sources as release_sources_api

    monkeypatch.setattr(release_sources_api, "resolve_listing_parser", lambda *_args, **_kwargs: _Parser())
    monkeypatch.setattr(release_sources_api, "_http_get", lambda *_args, **_kwargs: "<html></html>")

    response = client.post("/api/release-sources/health-check")
    assert response.status_code == 200

    payload = response.json()
    assert payload["total_sources"] == 1
    assert payload["passed_sources"] == 1
    assert payload["failed_sources"] == 0
    assert payload["results"][0]["passed"] is True
    assert payload["results"][0]["latest_article_url"] == "https://news.kalshi.com/p/latest"


def test_release_source_health_check_uses_generic_fallback_when_no_dedicated_parser(client, monkeypatch):
    created = client.post(
        "/api/release-sources",
        json={
            "company_name": "Unknown",
            "category": "Other",
            "source_url": "https://unknown.example/news",
            "notes": "",
            "is_active": True,
        },
    )
    assert created.status_code == 201

    from app.api import release_sources as release_sources_api

    monkeypatch.setattr(release_sources_api, "resolve_listing_parser", lambda *_args, **_kwargs: None)

    listing_html = '<a href="https://unknown.example/news/2026/03/release-1.html">Release</a>'
    article_html = (
        '<html><head>'
        '<title>Unknown Release</title>'
        '<meta property="article:published_time" content="2026-03-20T10:00:00Z" />'
        '</head><body>Release body</body></html>'
    )

    def fake_http_get(url: str, timeout: int = 20):
        if url == "https://unknown.example/news":
            return listing_html
        if url == "https://unknown.example/news/2026/03/release-1.html":
            return article_html
        return "<html></html>"

    monkeypatch.setattr(release_sources_api, "_http_get", fake_http_get)

    response = client.post("/api/release-sources/health-check")
    assert response.status_code == 200

    payload = response.json()
    assert payload["total_sources"] == 1
    assert payload["passed_sources"] == 1
    assert payload["failed_sources"] == 0
    assert payload["results"][0]["passed"] is True
    assert payload["results"][0]["latest_article_url"] == "https://unknown.example/news/2026/03/release-1.html"


def test_single_release_source_health_check_returns_result_for_selected_company(client, monkeypatch):
    created = client.post(
        "/api/release-sources",
        json={
            "company_name": "Evolution",
            "category": "Supplier",
            "source_url": "https://www.evolution.com/news",
            "notes": "",
            "is_active": True,
        },
    )
    assert created.status_code == 201
    source_id = created.json()["id"]

    class _Parser:
        def parse_listing(self, **kwargs):
            class _Parsed:
                candidate_urls = ["https://www.evolution.com/news/latest/"]
                candidate_titles = {"https://www.evolution.com/news/latest/": "Latest Evolution"}
                candidate_published_dates = {"https://www.evolution.com/news/latest/": datetime.datetime(2026, 3, 28, 9, 0, 0)}
                empty_reason = None

            return _Parsed()

        def extract_article_published_date(self, _: str):
            return datetime.datetime(2026, 3, 28, 9, 0, 0)

    from app.api import release_sources as release_sources_api

    monkeypatch.setattr(release_sources_api, "resolve_listing_parser", lambda *_args, **_kwargs: _Parser())
    monkeypatch.setattr(release_sources_api, "_http_get", lambda *_args, **_kwargs: "<html></html>")

    response = client.post(f"/api/release-sources/health-check/{source_id}")
    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "success"
    assert payload["result"]["source_id"] == source_id
    assert payload["result"]["passed"] is True
    assert payload["result"]["latest_article_url"] == "https://www.evolution.com/news/latest/"


def test_single_release_source_health_check_returns_404_when_source_missing(client):
    response = client.post("/api/release-sources/health-check/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Release source not found"
