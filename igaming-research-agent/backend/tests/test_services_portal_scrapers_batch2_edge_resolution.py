from app.services.portal_scrapers.parsers.ags_html import AgsHtmlParser
from app.services.portal_scrapers.parsers.bet365_html import Bet365HtmlParser
from app.services.portal_scrapers.registry import resolve_listing_parser


def test_batch2_edge_sources_resolution():
    ags = resolve_listing_parser('https://newsroom.playags.com', 'AGS (PlayAGS)')
    bet365 = resolve_listing_parser(
        'https://news.bet365.com/en-us/sport/more-sports-and-news/2022102012405478121',
        'Bet365',
    )

    assert isinstance(ags, AgsHtmlParser)
    assert isinstance(bet365, Bet365HtmlParser)
