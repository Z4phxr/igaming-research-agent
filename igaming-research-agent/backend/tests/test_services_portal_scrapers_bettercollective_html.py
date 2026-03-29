import datetime

from app.services.portal_scrapers.parsers.bettercollective_html import BetterCollectiveHtmlParser


def test_bettercollective_parser_extracts_release_links_with_dates():
    parser = BetterCollectiveHtmlParser()
    listing_html = """
    <div>
      <a href='https://bettercollective.com/press-releases/better-collective-expands-into-prediction-markets'>Better Collective expands into prediction markets</a>
      <span>19/03/2026, 14:30:00</span>
    </div>
    <div>
      <a href='https://bettercollective.com/press-releases/share-buyback-program-march-18-march-24-2026'>Share buyback program (March 18 - March 24, 2026)</a>
      <span>25/03/2026, 12:00:00</span>
    </div>
    """

    result = parser.parse_listing(listing_html, "https://bettercollective.com/press-releases/", "Better Collective")

    assert result.empty_reason is None
    assert len(result.candidate_urls) == 2
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 19)
