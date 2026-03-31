import datetime

from app.services.portal_scrapers.parsers.ic360_html import Ic360HtmlParser


def test_ic360_parser_extracts_media_links_and_dates():
    parser = Ic360HtmlParser()
    listing_html = """
    <div>
      <a href='https://ic360.io/page/ic360-and-pac-12-conference-expand-partnership-with-integration-of-prohibet'>IC360 and Pac-12 Conference Expand Partnership with Integration of ProhiBet</a>
      <span>Partnership Mar 17, 2026</span>
    </div>
    <div>
      <a href='https://ic360.io/page/ncaa-bolsters-competition-integrity-with-ic360%E2%80%99s-prohibet-solution-for-championship-officials'>NCAA Bolsters Competition Integrity with IC360's ProhiBet Solution</a>
      <span>Press Release Mar 10, 2026</span>
    </div>
    """

    result = parser.parse_listing(
        listing_html=listing_html,
        source_url="https://ic360.io/media",
        company_name="IC360",
    )

    assert result.empty_reason is None
    assert len(result.candidate_urls) == 2
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 17)
