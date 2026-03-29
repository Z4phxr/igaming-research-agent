import datetime

from app.services.portal_scrapers.parsers.prizepicks_html import PrizePicksHtmlParser


def test_prizepicks_parser_extracts_press_news_links_and_dates():
    parser = PrizePicksHtmlParser()
    listing_html = """
    <a href='https://www.prizepicks.com/press-news/prizepicks-inks-exclusive-always-on-partnership-with-bob-does-sports'>PrizePicks Inks Exclusive Always-On Partnership with Bob Does Sports</a>
    <span>March 3, 2026</span>
    <a href='https://www.prizepicks.com/press-news/prizepicks-sets-record-for-prediction-markets-engagement-on-big-game-sunday'>PrizePicks Sets Record for Prediction Markets Engagement on Big Game Sunday</a>
    <span>February 10, 2026</span>
    """

    result = parser.parse_listing(listing_html, "https://www.prizepicks.com/newsroom", "PrizePicks")

    assert result.empty_reason is None
    assert len(result.candidate_urls) == 2
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 3)
