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


def test_rsi_parser_fetches_q4_public_feed_when_listing_is_dynamic(monkeypatch):
    parser = RsiHtmlParser()
    listing_html = """
    <div class='evergreen evergreen-news'></div>
    <script>
      $tudio('#_ctrl0_ctl55_divModuleContainer').q4News({
        category: '1cb807d2-208f-4bc3-9133-6a9ad45ac3b0'
      });
    </script>
    """

    class _FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "GetPressReleaseListResult": [
                    {
                        "Headline": "RSI Announces Quarterly Results",
                        "LinkToDetailPage": "/news/news-details/2026/rsi-announces-quarterly-results/default.aspx",
                        "PressReleaseDate": "2026-03-20T09:00:00",
                    }
                ]
            }

    def _fake_get(*args, **kwargs):
        return _FakeResponse()

    monkeypatch.setattr("app.services.portal_scrapers.parsers.rsi_html.requests.get", _fake_get)

    result = parser.parse_listing(
        listing_html=listing_html,
        source_url="https://ir.rushstreetinteractive.com/news/default.aspx",
        company_name="BetRivers / Rush Street Interactive",
    )

    assert result.empty_reason is None
    assert result.candidate_urls == [
        "https://ir.rushstreetinteractive.com/news/news-details/2026/rsi-announces-quarterly-results/default.aspx"
    ]
    assert result.candidate_titles[result.candidate_urls[0]] == "RSI Announces Quarterly Results"
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 20, 9, 0, 0)
