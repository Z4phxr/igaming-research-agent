import datetime

from app.services.portal_scrapers.parsers.igt_html import IgtHtmlParser


def test_igt_parser_extracts_newsroom_details_links_and_dates():
    parser = IgtHtmlParser()
    listing_html = """
    <a href='/Explore IGT/News/News Room Details?Index=20260325213d'>IGT Shapes the Future of Gaming for Tribal Casino Operators at the 2026 Indian Gaming Tradeshow & Convention 03/25/2026</a>
    <a href='/Explore IGT/News/News Room Details?Index=20260318add7'>IGT Launches National Advertising Campaign Commemorating the 30th Anniversary of Wheel of Fortune Slots 03/18/2026</a>
    """

    result = parser.parse_listing(listing_html, "https://www.igt.com/explore-igt/news/news", "IGT (+ Everi)")

    assert result.empty_reason is None
    assert result.candidate_urls[0].endswith("Index=20260325213d")
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 25)
