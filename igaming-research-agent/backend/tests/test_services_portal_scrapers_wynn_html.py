import datetime

from app.services.portal_scrapers.parsers.wynn_html import WynnHtmlParser


def test_wynn_parser_extracts_links_titles_and_dates():
    parser = WynnHtmlParser()
    listing_html = """
    <table class='table'>
      <tbody>
        <tr>
          <td><time>03/11/26</time></td>
          <td>
            <a class='more-item' href='/news-releases/news-release-details/wynn-resorts-issues-update-wynn-al-marjan-island'>
              <span class='more-item__text'>Wynn Resorts Issues Update on Wynn Al Marjan Island</span>
            </a>
          </td>
        </tr>
        <tr>
          <td><time>02/12/26</time></td>
          <td>
            <a class='more-item' href='/news-releases/news-release-details/wynn-resorts-limited-reports-fourth-quarter-and-year-end-2025'>
              <span class='more-item__text'>Wynn Resorts, Limited Reports Fourth Quarter and Year End 2025 Results</span>
            </a>
          </td>
        </tr>
      </tbody>
    </table>
    """

    result = parser.parse_listing(listing_html, "https://investors.wynnresorts.com/press-releases", "WynnBET")

    assert result.empty_reason is None
    assert (
      result.candidate_urls[0]
      == "https://investors.wynnresorts.com/news-releases/news-release-details/wynn-resorts-issues-update-wynn-al-marjan-island"
    )
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 11)
