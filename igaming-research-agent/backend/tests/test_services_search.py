from app.models import Query
from app.services import search


class MockResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "news": [
                {"title": "A", "link": "https://a.example", "snippet": "alpha"},
                {"title": "B", "link": "https://b.example", "snippet": "beta"},
            ]
        }


def test_get_active_queries_returns_only_active(db_session):
    db_session.add_all(
        [
            Query(search_term="one", stream_type="business", is_active=True),
            Query(search_term="two", stream_type="business", is_active=False),
        ]
    )
    db_session.commit()

    active = search.get_active_queries(db_session)

    assert len(active) == 1
    assert active[0].search_term == "one"


def test_execute_search_maps_results(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "test-key")

    query = Query(search_term="igaming", stream_type="business", is_active=True)

    def fake_post(url, headers, json, timeout):
        assert url == "https://google.serper.dev/news"
        assert headers["X-API-KEY"] == "test-key"
        assert json["q"] == "igaming"
        assert json["num"] == 10
        assert json["tbs"] == "qdr:d"
        assert timeout == 10
        return MockResponse()

    monkeypatch.setattr(search.requests, "post", fake_post)

    result = search.execute_search(query)

    assert result == [
        {
            "title": "A",
            "url": "https://a.example",
            "snippet": "alpha",
            "source": "",
            "published_date": None,
        },
        {
            "title": "B",
            "url": "https://b.example",
            "snippet": "beta",
            "source": "",
            "published_date": None,
        },
    ]


def test_execute_search_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    query = Query(search_term="igaming", stream_type="business", is_active=True)

    try:
        search.execute_search(query)
        assert False, "Expected RuntimeError when SERPER_API_KEY is missing"
    except RuntimeError as exc:
        assert "SERPER_API_KEY is missing" in str(exc)


def test_run_search_pipeline_deduplicates_urls(db_session, monkeypatch):
    db_session.add_all(
        [
            Query(search_term="q1", stream_type="business", is_active=True),
            Query(search_term="q2", stream_type="legislative", is_active=True),
        ]
    )
    db_session.commit()

    monkeypatch.setenv("SERPER_API_KEY", "test-key")

    def fake_execute(query):
        if query.search_term == "q1":
            return [
                {"title": "A", "url": "https://dup.example", "snippet": "1", "source": "", "published_date": None},
                {"title": "B", "url": "https://u1.example", "snippet": "2", "source": "", "published_date": None},
            ]
        return [
            {"title": "C", "url": "https://dup.example", "snippet": "3", "source": "", "published_date": None},
            {"title": "D", "url": "https://u2.example", "snippet": "4", "source": "", "published_date": None},
        ]

    monkeypatch.setattr(search, "execute_search", fake_execute)

    result = search.run_search_pipeline(db_session)

    assert [item["url"] for item in result] == [
        "https://dup.example",
        "https://u1.example",
        "https://u2.example",
    ]
