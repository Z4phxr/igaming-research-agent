from app.services.portal_scrapers.parsers.aga_html import AgaHtmlParser
from app.services.portal_scrapers.parsers.bettercollective_html import BetterCollectiveHtmlParser
from app.services.portal_scrapers.parsers.catenamedia_html import CatenaMediaHtmlParser
from app.services.portal_scrapers.parsers.gdcgroup_html import GdcGroupHtmlParser
from app.services.portal_scrapers.parsers.geniussports_html import GeniusSportsHtmlParser
from app.services.portal_scrapers.parsers.polymarket_prnewswire_html import PolymarketPrnewswireHtmlParser
from app.services.portal_scrapers.parsers.prizepicks_html import PrizePicksHtmlParser
from app.services.portal_scrapers.parsers.sportradar_html import SportradarHtmlParser
from app.services.portal_scrapers.registry import resolve_listing_parser


def test_batch4_registry_resolution_matrix():
    cases = [
        ("https://www.gdcgroup.com/media-center", "Gambling.com Group", GdcGroupHtmlParser),
        ("https://bettercollective.com/press-releases/", "Better Collective", BetterCollectiveHtmlParser),
        ("https://www.catenamedia.com/investors/press-releases", "Catena Media", CatenaMediaHtmlParser),
        ("https://sportradar.com/content-hub/", "Sportradar", SportradarHtmlParser),
        ("https://www.geniussports.com/newsroom/", "Genius Sports", GeniusSportsHtmlParser),
        ("https://www.americangaming.org/newsroom/", "American Gaming Association (AGA)", AgaHtmlParser),
        ("https://www.prizepicks.com/newsroom", "PrizePicks", PrizePicksHtmlParser),
        ("https://www.prnewswire.com/news/polymarket/", "Polymarket", PolymarketPrnewswireHtmlParser),
    ]

    for source_url, company_name, expected in cases:
        parser = resolve_listing_parser(source_url, company_name)
        assert isinstance(parser, expected)
