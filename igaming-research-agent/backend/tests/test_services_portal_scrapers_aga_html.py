import datetime

from app.services.portal_scrapers.parsers.aga_html import AgaHtmlParser


def test_aga_parser_extracts_newsroom_links_and_dates():
    parser = AgaHtmlParser()
    listing_html = """
    <a href='https://www.americangaming.org/americans-to-legally-wager-3-3-billion-on-march-madness-nearly-half-of-digital-sports-betting-ads-now-come-from-prediction-market-platforms/'>Americans to Legally Wager $3.3 Billion on March Madness</a>
    <span>March 13, 2026</span>
    <a href='https://www.americangaming.org/commercial-gaming-revenue-hits-78-7-billion-in-2025-driving-record-18-1-billion-in-gaming-taxes-nationwide/'>Commercial Gaming Revenue Hits $78.7 Billion in 2025</a>
    <span>February 26, 2026</span>
    """

    result = parser.parse_listing(listing_html, "https://www.americangaming.org/newsroom/", "American Gaming Association")

    assert result.empty_reason is None
    assert len(result.candidate_urls) == 2
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 13)
