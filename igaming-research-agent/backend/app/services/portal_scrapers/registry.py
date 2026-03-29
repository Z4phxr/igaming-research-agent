from __future__ import annotations

from app.services.portal_scrapers.base import PortalListingParser
from app.services.portal_scrapers.parsers.betmgm_html import BetMgmHtmlParser
from app.services.portal_scrapers.parsers.config_driven_html import ConfigDrivenHtmlParser, HtmlListingParserConfig
from app.services.portal_scrapers.parsers.evolution_html import EvolutionHtmlParser
from app.services.portal_scrapers.parsers.fanduel_html import FanDuelHtmlParser
from app.services.portal_scrapers.parsers.kalshi_html import KalshiHtmlParser


_PARSERS: list[PortalListingParser] = [
    BetMgmHtmlParser(),
    EvolutionHtmlParser(),
    FanDuelHtmlParser(),
    KalshiHtmlParser(),
]

_CONFIG_DRIVEN_CONFIGS: list[HtmlListingParserConfig] = [
    # Template-like starter config to speed up onboarding of simple HTML listing portals.
    HtmlListingParserConfig(
        name="demo-config-driven-portal",
        source_url_contains=("config-driven.example",),
        item_selector="article.release-item",
        link_selector="a[href]",
        title_selector="h2, h3",
        date_selector="time",
        date_formats=("%Y-%m-%d",),
        descending_chronological=True,
        empty_reason_no_items="no_config_release_items",
    )
]

_CONFIG_DRIVEN_PARSER = ConfigDrivenHtmlParser(_CONFIG_DRIVEN_CONFIGS)


def resolve_listing_parser(source_url: str, company_name: str) -> PortalListingParser | None:
    for parser in _PARSERS:
        if parser.matches(source_url=source_url, company_name=company_name):
            return parser
    if _CONFIG_DRIVEN_PARSER.matches(source_url=source_url, company_name=company_name):
        return _CONFIG_DRIVEN_PARSER
    return None


def list_registered_parsers() -> list[PortalListingParser]:
    return list(_PARSERS) + [_CONFIG_DRIVEN_PARSER]
