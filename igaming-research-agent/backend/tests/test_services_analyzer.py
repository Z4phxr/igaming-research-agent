import importlib
import os

import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from app.services import analyzer


class MockCompletionResponse:
    class Block:
        def __init__(self, text):
            self.text = text

    def __init__(self, content):
        self.content = [self.Block(content)]


def test_module_raises_when_anthropic_key_missing(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY is missing"):
        import app.services.analyzer as analyzer_module

        importlib.reload(analyzer_module)


def test_is_relevant_returns_true_for_yes_response(monkeypatch):
    def fake_create(**kwargs):
        assert kwargs["model"] == analyzer._MODEL
        assert kwargs["max_tokens"] == 10
        assert kwargs["temperature"] == 0
        assert kwargs["system"]
        assert kwargs["messages"][0]["role"] == "user"
        return MockCompletionResponse("YES")

    monkeypatch.setattr(analyzer.anthropic_client.messages, "create", fake_create)

    result = analyzer.is_relevant(
        {
            "title": "US iGaming legislation update",
            "snippet": "A state passed a sports betting bill",
            "full_text": "",
            "url": "https://example.com/a",
        }
    )

    assert result is True


def test_score_and_summarize_parses_expected_format(monkeypatch):
    def fake_create(**kwargs):
        assert kwargs["model"] == analyzer._MODEL
        assert kwargs["max_tokens"] == 200
        assert kwargs["temperature"] == 0
        assert kwargs["system"]
        assert "Content:" in kwargs["messages"][0]["content"]
        return MockCompletionResponse(
            "SCORE: 8\n"
            "SUMMARY: First sentence explains the legislative update in detail with a clear policy timeline. "
            "Second sentence covers operator impact with revenue context and commission decision framing. "
            "Third sentence highlights near-term business implications and expected market response.\n"
            "TAGS: legislation, regulation"
        )

    monkeypatch.setattr(analyzer.anthropic_client.messages, "create", fake_create)

    result = analyzer.score_and_summarize(
        {
            "title": "US iGaming policy",
            "snippet": "snippet",
            "full_text": "full text " * 500,
            "url": "https://example.com/article",
            "source_domain": "example.com",
        }
    )

    assert result is not None
    assert result["score"] == 8
    assert "First sentence explains the legislative update" in result["summary"]
    assert result["tags"] == "legislation, regulation"


def test_run_analysis_pipeline_filters_and_sorts(monkeypatch):
    articles = [
        {"title": "A", "snippet": "A", "full_text": "A", "url": "https://a", "source_domain": "a.com"},
        {"title": "B", "snippet": "B", "full_text": "B", "url": "https://b", "source_domain": "b.com"},
        {"title": "C", "snippet": "C", "full_text": "C", "url": "https://c", "source_domain": "c.com"},
    ]

    relevance = {"https://a": True, "https://b": True, "https://c": False}
    scored = {
        "https://a": {**articles[0], "score": 9, "summary": "sum", "tags": "regulation"},
        "https://b": {**articles[1], "score": 5, "summary": "sum", "tags": "technology"},
    }

    monkeypatch.setattr(analyzer, "is_relevant", lambda article: relevance[article["url"]])
    monkeypatch.setattr(analyzer, "score_and_summarize", lambda article: scored.get(article["url"]))

    result = analyzer.run_analysis_pipeline(articles)

    assert len(result["final_articles"]) == 1
    assert result["final_articles"][0]["url"] == "https://a"
    assert len(result["all_articles"]) == 3


def test_is_relevant_article_compat_alias(monkeypatch):
    monkeypatch.setattr(analyzer, "is_relevant", lambda article: True)

    assert analyzer.is_relevant_article("text body") is True


def test_score_and_summarize_returns_none_on_parse_error(monkeypatch):
    monkeypatch.setattr(analyzer.anthropic_client.messages, "create", lambda **kwargs: MockCompletionResponse("invalid"))

    result = analyzer.score_and_summarize(
        {
            "title": "bad",
            "snippet": "bad",
            "full_text": "bad",
            "url": "https://bad",
            "source_domain": "bad.com",
        }
    )

    assert result is None
