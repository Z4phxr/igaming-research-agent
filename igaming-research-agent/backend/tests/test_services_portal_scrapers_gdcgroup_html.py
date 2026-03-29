import datetime

from app.services.portal_scrapers.parsers.gdcgroup_html import GdcGroupHtmlParser


def test_gdcgroup_parser_extracts_media_center_links_and_dates():
    parser = GdcGroupHtmlParser()
    listing_html = """
    <a href='https://www.gdcgroup.com/media-center/gambling-com-group-ready-for-launch-of-online-sports-betting-in-missouri'>Gambling.com Group Ready for Launch of Online Sports Betting in Missouri</a>
    <span>December 1st, 2025</span>
    <a href='https://www.gdcgroup.com/media-center/gambling-com-group-announces-2025-american-gambling-awards-winners'>Gambling.com Group Announces 2025 American Gambling Awards Winners</a>
    <span>November 19th, 2025</span>
    """

    result = parser.parse_listing(listing_html, "https://www.gdcgroup.com/media-center", "Gambling.com Group")

    assert result.empty_reason is None
    assert len(result.candidate_urls) == 2
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2025, 12, 1)
