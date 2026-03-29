from app.services.portal_scrapers.parsers.aristocrat_html import AristocratHtmlParser
from app.services.portal_scrapers.parsers.bally_html import BallyHtmlParser
from app.services.portal_scrapers.parsers.igt_html import IgtHtmlParser
from app.services.portal_scrapers.parsers.lnw_html import LnwHtmlParser
from app.services.portal_scrapers.parsers.underdog_html import UnderdogHtmlParser
from app.services.portal_scrapers.parsers.wynn_html import WynnHtmlParser
from app.services.portal_scrapers.registry import resolve_listing_parser


def test_batch2_registry_resolution_matrix():
    cases = [
        ("https://www.aristocrat.com/news/", "Aristocrat Leisure", AristocratHtmlParser),
        ("https://www.ballys.com/news/default.aspx", "Bally's Interactive", BallyHtmlParser),
        ("https://www.igt.com/explore-igt/news/news", "IGT (+ Everi)", IgtHtmlParser),
        ("https://explore.lnw.com/newsroom/", "Light & Wonder", LnwHtmlParser),
        ("https://www.underdogfantasy.com/news", "Underdog Fantasy", UnderdogHtmlParser),
        ("https://investors.wynnresorts.com/press-releases", "WynnBET", WynnHtmlParser),
    ]

    for source_url, company_name, expected in cases:
        parser = resolve_listing_parser(source_url, company_name)
        assert isinstance(parser, expected)
