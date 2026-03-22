from app.services import scraper


class MockResponse:
    def raise_for_status(self):
        return None

    @property
    def text(self):
        return "<html><body><h1>Headline</h1><p>Long article text.</p></body></html>"


def test_fetch_article_text_returns_extracted_payload(monkeypatch):
    def fake_get(url, timeout):
        assert url == "https://example.com/story"
        assert timeout == 10
        return MockResponse()

    monkeypatch.setattr(scraper.requests, "get", fake_get)

    class FakeTrafilatura:
        @staticmethod
        def extract(html, include_comments=False):
            return "Extracted text"

    monkeypatch.setattr(scraper, "trafilatura", FakeTrafilatura)

    payload = scraper.fetch_article_text("https://example.com/story")

    assert payload is not None
    assert payload["url"] == "https://example.com/story"
    assert payload["full_text"] == "Extracted text"
    assert payload["source_domain"] == "example.com"


def test_fetch_article_text_returns_none_on_request_error(monkeypatch):
    def fake_get(url, timeout):
        raise scraper.requests.Timeout("timed out")

    monkeypatch.setattr(scraper.requests, "get", fake_get)

    text = scraper.fetch_article_text("https://example.com/fail")

    assert text is None


def test_fetch_article_text_returns_none_when_extraction_none(monkeypatch):
    monkeypatch.setattr(scraper.requests, "get", lambda url, timeout: MockResponse())

    class FakeTrafilatura:
        @staticmethod
        def extract(html, include_comments=False):
            return None

    monkeypatch.setattr(scraper, "trafilatura", FakeTrafilatura)

    text = scraper.fetch_article_text("https://example.com/unreadable")

    assert text is None


def test_extract_source_domain():
    domain = scraper.extract_source_domain("https://news.example.com/path")

    assert domain == "news.example.com"


def test_scrape_articles_merges_full_text(monkeypatch):
    articles = [
        {
            "title": "Story",
            "url": "https://example.com/a",
            "snippet": "snippet",
            "source": "example",
            "published_date": "2026-01-01",
        }
    ]

    monkeypatch.setattr(
        scraper,
        "fetch_article_text",
        lambda url: {"url": url, "full_text": "Full body", "source_domain": "example.com"},
    )

    result = scraper.scrape_articles(articles)

    assert len(result) == 1
    assert result[0]["full_text"] == "Full body"
    assert result[0]["source_domain"] == "example.com"


def test_scrape_articles_empty_input_returns_empty_list():
    result = scraper.scrape_articles([])

    assert result == []
