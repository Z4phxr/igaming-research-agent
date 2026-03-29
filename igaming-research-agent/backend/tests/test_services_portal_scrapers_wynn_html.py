import datetime

from app.services.portal_scrapers.parsers.wynn_html import WynnHtmlParser


def test_wynn_parser_extracts_links_titles_and_dates():
    parser = WynnHtmlParser()
    listing_html = """
    <table>
      <tr><td>03/11/26</td><td><a href='/press-releases/wynn-resorts-issues-update-on-wynn-al-marjan-island'>Wynn Resorts Issues Update on Wynn Al Marjan Island</a></td></tr>
      <tr><td>02/12/26</td><td><a href='/press-releases/wynn-resorts-limited-reports-fourth-quarter-and-year-end-2025-results'>Wynn Resorts, Limited Reports Fourth Quarter and Year End 2025 Results</a></td></tr>
    </table>
    """

    result = parser.parse_listing(listing_html, "https://investors.wynnresorts.com/press-releases", "WynnBET")

    assert result.empty_reason is None
    assert result.candidate_urls[0] == "https://investors.wynnresorts.com/press-releases/wynn-resorts-issues-update-on-wynn-al-marjan-island"
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 11)
