import datetime

from app.services.portal_scrapers.parsers.bragg_html import BraggHtmlParser


def test_bragg_parser_extracts_release_links_and_dates():
    parser = BraggHtmlParser()
    listing_html = """
    <div>
      <a href='https://bragg.group/bragg-is-shortlisted-in-4-categories-for-the-sbc-awards-europe-2026/'>Bragg is shortlisted in 4 categories for the SBC Awards Europe 2026!</a>
      <span>March 25, 2026</span>
    </div>
    <div>
      <a href='https://bragg.group/meet-bragg-at-bis-sigma-south-america/'>Meet Bragg at BiS SiGMA South America!</a>
      <span>March 19, 2026</span>
    </div>
    <a href='https://bragg.group/news/page/2/'>2</a>
    """

    result = parser.parse_listing(
        listing_html=listing_html,
        source_url="https://bragg.group/news/",
        company_name="Bragg",
    )

    assert result.empty_reason is None
    assert len(result.candidate_urls) == 2
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 25)
