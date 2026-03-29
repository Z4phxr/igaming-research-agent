import datetime

from app.services.portal_scrapers.parsers.catenamedia_html import CatenaMediaHtmlParser


def test_catenamedia_parser_extracts_release_links_and_dates():
    parser = CatenaMediaHtmlParser()
    listing_html = """
    <a href='https://www.catenamedia.com/release/catena-media-publishes-its-2025-annual-report/'>Catena Media publishes its 2025 annual report</a>
    <span>MARCH 24TH, 2026 21:30 CET REGULATORY</span>
    <a href='https://www.catenamedia.com/release/a-solid-quarter-of-revenue-growth-and-improved-profitability/'>A solid quarter of revenue growth and improved profitability</a>
    <span>FEBRUARY 6TH, 2026 17:00 CET</span>
    """

    result = parser.parse_listing(listing_html, "https://www.catenamedia.com/investors/press-releases", "Catena Media")

    assert result.empty_reason is None
    assert len(result.candidate_urls) == 2
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 24)
