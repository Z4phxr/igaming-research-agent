from app.services.portal_scrapers.registry import resolve_listing_parser
from app.services.portal_scrapers.parsers.kalshi_html import KalshiHtmlParser


def test_registry_resolves_kalshi_parser_for_kalshi_source():
    parser = resolve_listing_parser("https://news.kalshi.com/t/announcements", "Kalshi")
    assert isinstance(parser, KalshiHtmlParser)


def test_registry_returns_none_for_unknown_source():
    parser = resolve_listing_parser("https://example.com/news", "Example Corp")
    assert parser is None
