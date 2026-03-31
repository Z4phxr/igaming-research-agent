import datetime

from app.services.portal_scrapers.parsers.geocomply_html import GeocomplyHtmlParser


def test_geocomply_parser_extracts_press_coverage_links_and_dates():
    parser = GeocomplyHtmlParser()
    listing_html = """
    <article>
      <h5>GeoComply named Financial Transaction Security Platform of the Year</h5>
      <a href='https://www.geocomply.com/news/geocomply-named-financial-transaction-security-platform-of-the-year-for-second-year-in-a-row/'>Learn more</a>
      <span>Mar 19, 2026</span>
    </article>
    <article>
      <h5>GeoComply's unified identity platform helps Brazil iGaming operators</h5>
      <a href='https://www.geocomply.com/news/geocomplys-unified-identity-platform-helps-brazil-igaming-operators-increase-pass-rates-while-strengthening-fraud-protection/'>Learn more</a>
      <span>Jan 19, 2026</span>
    </article>
    """

    result = parser.parse_listing(
        listing_html=listing_html,
        source_url="https://www.geocomply.com/awards-and-press/",
        company_name="GeoComply",
    )

    assert result.empty_reason is None
    assert len(result.candidate_urls) == 2
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 19)
