import datetime

from app.services.portal_scrapers.parsers.rsi_html import RsiHtmlParser


def test_rsi_parser_extracts_links_titles_and_dates_when_present():
    parser = RsiHtmlParser()
    listing_html = """
    <div class='news-item'>
      March 22, 2026
      <a href='/news-releases/news-release-details/rsi-announces-new-launch'>RSI Announces New Launch</a>
    </div>
    <div class='news-item'>
      March 12, 2026
      <a href='/news-releases/news-release-details/rsi-reports-quarterly-results'>RSI Reports Quarterly Results</a>
    </div>
    """

    result = parser.parse_listing(
        listing_html=listing_html,
        source_url="https://ir.rushstreetinteractive.com/news/default.aspx",
        company_name="BetRivers / Rush Street Interactive",
    )

    assert result.empty_reason is None
    assert result.candidate_urls == [
        "https://ir.rushstreetinteractive.com/news-releases/news-release-details/rsi-announces-new-launch",
        "https://ir.rushstreetinteractive.com/news-releases/news-release-details/rsi-reports-quarterly-results",
    ]
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 22)


def test_rsi_parser_returns_auth_reason_when_q4_login_required():
    parser = RsiHtmlParser()
    listing_html = "https://auth.platform.q4inc.com/auth/publicAuthRedirect?error=login_required"

    result = parser.parse_listing(
        listing_html=listing_html,
        source_url="https://ir.rushstreetinteractive.com/news/default.aspx",
        company_name="BetRivers / Rush Street Interactive",
    )

    assert result.candidate_urls == []
    assert result.empty_reason == "q4_auth_required"


def test_rsi_parser_returns_dynamic_listing_reason_when_no_static_links():
    parser = RsiHtmlParser()
    listing_html = "<div class='evergreen evergreen-news'><script src='/js/module/widgets/dist/latest/evergreen.q4Api.min.js'></script></div>"

    result = parser.parse_listing(
        listing_html=listing_html,
        source_url="https://ir.rushstreetinteractive.com/news/default.aspx",
        company_name="BetRivers / Rush Street Interactive",
    )

    assert result.candidate_urls == []
    assert result.empty_reason == "q4_dynamic_listing_no_static_links"
