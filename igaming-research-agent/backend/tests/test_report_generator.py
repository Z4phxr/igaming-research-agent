from app.services import report_generator


class MockClaudeResponse:
    class Block:
        def __init__(self, text: str):
            self.text = text

    def __init__(self, text: str):
        self.content = [self.Block(text)]


def test_generate_briefing_returns_string_on_success(monkeypatch):
    def fake_create(**kwargs):
        assert kwargs["model"] == "claude-sonnet-4-6"
        assert kwargs["max_tokens"] == 2000
        assert kwargs["temperature"] == 0.3
        assert "Today's top iGaming stories" in kwargs["messages"][0]["content"]
        return MockClaudeResponse("## Executive Summary\nBriefing body")

    monkeypatch.setattr(report_generator.anthropic_client.messages, "create", fake_create)

    result = report_generator.generate_briefing(
        [
            {
                "title": "US gaming bill progresses",
                "summary": "Committee passed bill with bipartisan support.",
                "score": 8,
                "tags": "legislation, regulation",
                "source_domain": "example.com",
                "url": "https://example.com/story",
            }
        ]
    )

    assert isinstance(result, str)
    assert "Executive Summary" in result


def test_generate_briefing_returns_none_on_empty_articles():
    assert report_generator.generate_briefing([]) is None


def test_generate_briefing_returns_none_on_api_error(monkeypatch):
    def fake_create(**kwargs):
        raise RuntimeError("API unavailable")

    monkeypatch.setattr(report_generator.anthropic_client.messages, "create", fake_create)

    result = report_generator.generate_briefing(
        [
            {
                "title": "US gaming bill progresses",
                "summary": "Committee passed bill with bipartisan support.",
                "score": 8,
                "tags": "legislation, regulation",
                "source_domain": "example.com",
                "url": "https://example.com/story",
            }
        ]
    )

    assert result is None
