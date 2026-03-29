from app.services.portal_scrapers.parsers.bragg_html import BraggHtmlParser
from app.services.portal_scrapers.parsers.geocomply_html import GeocomplyHtmlParser
from app.services.portal_scrapers.parsers.ic360_html import Ic360HtmlParser
from app.services.portal_scrapers.parsers.kambi_html import KambiHtmlParser
from app.services.portal_scrapers.parsers.playtech_html import PlaytechHtmlParser
from app.services.portal_scrapers.parsers.pragmaticplay_html import PragmaticPlayHtmlParser
from app.services.portal_scrapers.parsers.scientificgames_html import ScientificGamesHtmlParser
from app.services.portal_scrapers.registry import resolve_listing_parser


def test_batch3_registry_resolution_matrix():
    cases = [
        ("https://www.playtech.com/category/press-releases/#grid", "Playtech", PlaytechHtmlParser),
        ("https://www.pragmaticplay.com/en/news/#", "Pragmatic Play", PragmaticPlayHtmlParser),
        ("https://bragg.group/news/", "Bragg", BraggHtmlParser),
        ("https://www.kambi.com/news-insights/", "Kambi", KambiHtmlParser),
        ("https://ic360.io/media", "IC360", Ic360HtmlParser),
        ("https://www.geocomply.com/awards-and-press/", "GeoComply", GeocomplyHtmlParser),
        ("https://www.scientificgames.com/news/", "Scientific Games", ScientificGamesHtmlParser),
    ]

    for source_url, company_name, expected in cases:
        parser = resolve_listing_parser(source_url, company_name)
        assert isinstance(parser, expected)
