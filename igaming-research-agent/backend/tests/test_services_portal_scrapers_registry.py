from app.services.portal_scrapers.parsers.betmgm_html import BetMgmHtmlParser
from app.services.portal_scrapers.parsers.config_driven_html import ConfigDrivenHtmlParser
from app.services.portal_scrapers.parsers.evolution_html import EvolutionHtmlParser
from app.services.portal_scrapers.parsers.fanduel_html import FanDuelHtmlParser
from app.services.portal_scrapers.registry import resolve_listing_parser
from app.services.portal_scrapers.parsers.kalshi_html import KalshiHtmlParser


def test_registry_resolves_kalshi_parser_for_kalshi_source():
    parser = resolve_listing_parser("https://news.kalshi.com/t/announcements", "Kalshi")
    assert isinstance(parser, KalshiHtmlParser)


def test_registry_returns_none_for_unknown_source():
    parser = resolve_listing_parser("https://example.com/news", "Example Corp")
    assert parser is None


def test_registry_resolves_evolution_parser_for_evolution_source():
    parser = resolve_listing_parser("https://www.evolution.com/news", "Evolution Gaming")
    assert isinstance(parser, EvolutionHtmlParser)


def test_registry_resolves_betmgm_parser_for_betmgm_source():
    parser = resolve_listing_parser("https://sports.betmgm.com/en/blog", "BetMGM")
    assert isinstance(parser, BetMgmHtmlParser)


def test_registry_resolves_fanduel_parser_for_fanduel_source():
    parser = resolve_listing_parser("https://www.fanduel.com/about/news", "FanDuel")
    assert isinstance(parser, FanDuelHtmlParser)


def test_registry_resolves_config_driven_parser_for_configured_source():
    parser = resolve_listing_parser("https://config-driven.example/news", "Demo Corp")
    assert isinstance(parser, ConfigDrivenHtmlParser)
