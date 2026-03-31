import datetime

import pytest

from app.services.portal_scrapers.parsers.kalshi_html import KalshiHtmlParser
from app.services.portal_scrapers.registry import list_registered_parsers


@pytest.mark.parametrize("parser", list_registered_parsers(), ids=lambda p: p.__class__.__name__)
def test_registered_portal_parsers_follow_base_contract(parser):
    # Every parser should provide deterministic contract outputs without running full pipeline.
    result = parser.parse_listing(
        listing_html="<html><body>empty</body></html>",
        source_url="https://example.com/listing",
        company_name="Example",
    )

    assert hasattr(result, "candidate_urls")
    assert hasattr(result, "empty_reason")
    assert isinstance(result.candidate_urls, list)
    assert result.empty_reason is None or isinstance(result.empty_reason, str)


@pytest.mark.parametrize("parser", list_registered_parsers(), ids=lambda p: p.__class__.__name__)
def test_registered_portal_parsers_date_hook_contract(parser):
    date_value = parser.extract_article_published_date("<html></html>")
    assert date_value is None or isinstance(date_value, datetime.datetime)


def test_kalshi_parser_only_listing_to_urls_without_pipeline():
    parser = KalshiHtmlParser()
    listing_html = (
        '{"web_title":"ARK Invest x Kalshi","slug":"ark-invest-kalshi-partnership-prediction-markets-research-risk-management"}'
        '{"web_title":"Policy Update","slug":"policy-update"}'
    )

    result = parser.parse_listing(
        listing_html=listing_html,
        source_url="https://news.kalshi.com/t/announcements",
        company_name="Kalshi",
    )

    assert result.candidate_urls == [
        "https://news.kalshi.com/p/ark-invest-kalshi-partnership-prediction-markets-research-risk-management",
        "https://news.kalshi.com/p/policy-update",
    ]


def test_kalshi_parser_only_article_date_extraction_without_pipeline():
    parser = KalshiHtmlParser()
    article_html = "<script>window.__NEXT_DATA__={\"datePublished\":\"2026-03-29T19:34:11.667Z\"};</script>"

    parsed = parser.extract_article_published_date(article_html)

    assert parsed is not None
    assert parsed.year == 2026
    assert parsed.month == 3
    assert parsed.day == 29
