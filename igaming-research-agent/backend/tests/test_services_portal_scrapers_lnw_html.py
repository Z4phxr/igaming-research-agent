import datetime

from app.services.portal_scrapers.parsers.lnw_html import LnwHtmlParser


def test_lnw_parser_extracts_newsroom_links_and_dates():
    parser = LnwHtmlParser()
    listing_html = """
    <div>
      03/26/2026
      <a href='/newsroom/light-wonder-secures-multiple-gaming-systems-agreements-across-north-america/'>Light & Wonder Secures Multiple Gaming Systems Agreements Across North America</a>
    </div>
    <div>
      03/24/2026
      <a href='/newsroom/light-wonder-to-unveil-expansive-portfolio-of-new-gaming-innovations-at-iga-2026/'>Light & Wonder to Unveil Expansive Portfolio of New Gaming Innovations at IGA 2026</a>
    </div>
    """

    result = parser.parse_listing(listing_html, "https://explore.lnw.com/newsroom/", "Light & Wonder")

    assert result.empty_reason is None
    assert result.candidate_urls[0] == "https://explore.lnw.com/newsroom/light-wonder-secures-multiple-gaming-systems-agreements-across-north-america/"
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 26)
