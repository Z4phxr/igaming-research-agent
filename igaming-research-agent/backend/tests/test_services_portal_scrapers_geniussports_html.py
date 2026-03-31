import datetime

from app.services.portal_scrapers.parsers.geniussports_html import GeniusSportsHtmlParser


def test_geniussports_parser_extracts_newsroom_links_and_dates():
    parser = GeniusSportsHtmlParser()
    listing_html = """
    <a href='https://www.geniussports.com/newsroom/digital-advertising-leaders-unite-around-genius-sports-moment-engine-for-real-time-activation/'>Digital advertising leaders unite around Genius Sports' Moment Engine</a>
    <span>26 Mar 2026</span>
    <a href='https://www.geniussports.com/newsroom/genius-sports-to-host-newfront-on-march-26-to-showcase-immersive-advertising-and-real-time-activation-solutions/'>Genius Sports to host NewFront</a>
    <span>19 Mar 2026</span>
    """

    result = parser.parse_listing(listing_html, "https://www.geniussports.com/newsroom/", "Genius Sports")

    assert result.empty_reason is None
    assert len(result.candidate_urls) == 2
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 26)
