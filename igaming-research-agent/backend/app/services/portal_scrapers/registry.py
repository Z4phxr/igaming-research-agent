from __future__ import annotations

from app.services.portal_scrapers.base import PortalListingParser
from app.services.portal_scrapers.parsers.kalshi_html import KalshiHtmlParser


_PARSERS: list[PortalListingParser] = [
    KalshiHtmlParser(),
]


def resolve_listing_parser(source_url: str, company_name: str) -> PortalListingParser | None:
    for parser in _PARSERS:
        if parser.matches(source_url=source_url, company_name=company_name):
            return parser
    return None


def list_registered_parsers() -> list[PortalListingParser]:
    return list(_PARSERS)
