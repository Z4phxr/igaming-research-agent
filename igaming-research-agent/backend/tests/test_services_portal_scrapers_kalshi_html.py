from app.services.portal_scrapers.parsers.kalshi_html import KalshiHtmlParser


def test_kalshi_parser_extracts_candidate_urls_and_dedupes():
    parser = KalshiHtmlParser()
    html = (
        '{"web_title":"ARK Invest x Kalshi","slug":"ark-invest-kalshi-partnership-prediction-markets"}'
        '{"web_title":"ARK Invest x Kalshi","slug":"ark-invest-kalshi-partnership-prediction-markets"}'
        '{"web_title":"Second Post","slug":"second-post"}'
    )

    result = parser.parse_listing(
        listing_html=html,
        source_url="https://news.kalshi.com/t/announcements",
        company_name="Kalshi",
    )

    assert result.empty_reason is None
    assert result.candidate_urls == [
        "https://news.kalshi.com/p/ark-invest-kalshi-partnership-prediction-markets",
        "https://news.kalshi.com/p/second-post",
    ]


def test_kalshi_parser_returns_dedicated_empty_reason_when_no_slug_found():
    parser = KalshiHtmlParser()
    result = parser.parse_listing(
        listing_html='<html><body><h1>No structured records</h1></body></html>',
        source_url="https://news.kalshi.com/t/announcements",
        company_name="Kalshi",
    )

    assert result.candidate_urls == []
    assert result.empty_reason == "no_structured_slug_found"


def test_kalshi_parser_extracts_article_date_published():
    parser = KalshiHtmlParser()
    article_html = '{"datePublished":"2026-03-26T19:34:11.667Z"}'

    parsed = parser.extract_article_published_date(article_html)

    assert parsed is not None
    assert parsed.year == 2026
    assert parsed.month == 3
    assert parsed.day == 26


def test_kalshi_parser_extracts_slug_from_anchor_href_variants():
    parser = KalshiHtmlParser()
    html = """
    <div>
      <a href="/post/first-update">First Update</a>
      <a href="https://news.kalshi.com/p/second-update?ref=listing">Second Update</a>
    </div>
    """

    result = parser.parse_listing(
        listing_html=html,
        source_url="https://news.kalshi.com/t/announcements",
        company_name="Kalshi",
    )

    assert result.candidate_urls == [
        "https://news.kalshi.com/p/first-update",
        "https://news.kalshi.com/p/second-update",
    ]
    assert result.candidate_titles[result.candidate_urls[0]] == "First Update"


def test_kalshi_parser_extracts_slug_from_script_json_object():
    parser = KalshiHtmlParser()
    html = '<script>{"slug":"script-only-release","title":"Script Only Release"}</script>'

    result = parser.parse_listing(
        listing_html=html,
        source_url="https://news.kalshi.com/t/announcements",
        company_name="Kalshi",
    )

    assert result.candidate_urls == ["https://news.kalshi.com/p/script-only-release"]
    assert result.candidate_titles[result.candidate_urls[0]] == "Script Only Release"
