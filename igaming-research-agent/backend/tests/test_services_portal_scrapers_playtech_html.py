import datetime

from app.services.portal_scrapers.parsers.playtech_html import PlaytechHtmlParser


def test_playtech_parser_extracts_press_release_links_and_dates():
    parser = PlaytechHtmlParser()
    listing_html = """
    <div>
      <a href='https://www.playtech.com/category/press-releases/page/2/#grid'>Next</a>
      <a href='https://www.playtech.com/playtech-announces-entry-into-sixth-regulated-igaming-state-with-connecticut-launch/'>Playtech announces entry into sixth regulated iGaming state with Connecticut Launch</a>
      <span>Press Releases 19 March 2026</span>
      <a href='https://www.playtech.com/playtech-launches-second-bespoke-game-exclusively-for-novibet/'>Playtech Launches Second Bespoke Game Exclusively for Novibet</a>
      <span>Press Releases 16 January 2026</span>
    </div>
    """

    result = parser.parse_listing(
        listing_html=listing_html,
        source_url="https://www.playtech.com/category/press-releases/#grid",
        company_name="Playtech",
    )

    assert result.empty_reason is None
    assert len(result.candidate_urls) == 2
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 19)
