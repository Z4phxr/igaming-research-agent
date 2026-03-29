import datetime

import requests

from app.services.portal_scrapers.parsers.bally_html import BallyHtmlParser


def test_bally_parser_returns_q4_auth_reason():
    parser = BallyHtmlParser()
    listing_html = "https://auth.platform.q4inc.com/auth/publicAuthRedirect?error=login_required"

    result = parser.parse_listing(listing_html, "https://www.ballys.com/news/default.aspx", "Bally's Interactive")

    assert result.candidate_urls == []
    assert result.empty_reason == "q4_auth_required"


def test_bally_parser_returns_dynamic_reason_when_widget_has_no_static_links(monkeypatch):
    parser = BallyHtmlParser()
    listing_html = """
    <div class='module_container--content' id='newsList'></div>
    <script>
      $('.module-news .module_container--widget').news({
        itemContainer: '.module_container--content',
        itemTemplate: '<a class="module_headline-link" href="{{url}}">{{title}}</a>'
      });
    </script>
    """

    def _failing_get(*args, **kwargs):
        raise requests.RequestException("request failed")

    # Force dynamic fetch path to fail so we assert the empty-reason fallback branch.
    monkeypatch.setattr("app.services.portal_scrapers.parsers.bally_html.requests.get", _failing_get)
    result = parser.parse_listing(listing_html, "https://www.ballys.com/news/default.aspx", "Bally's Interactive")

    assert result.candidate_urls == []
    assert result.empty_reason == "q4_dynamic_listing_no_static_links"


def test_bally_parser_fetches_q4_public_feed_when_listing_is_dynamic(monkeypatch):
    parser = BallyHtmlParser()
    listing_html = """
    <div class='module_container--content' id='newsList'></div>
    <script>
      $('.module-news .module_container--widget').news({
        itemContainer: '.module_container--content',
        itemTemplate: '<a class="module_headline-link" href="{{url}}">{{title}}</a>'
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
                        "Headline": "Bally's Interactive Announces New Product Rollout",
                        "LinkToDetailPage": "/news-releases/news-release-details/ballys-interactive-announces-new-product-rollout",
                        "PressReleaseDate": "03/24/2026 09:00:00",
                    }
                ]
            }

    def _fake_get(*args, **kwargs):
        return _FakeResponse()

    monkeypatch.setattr("app.services.portal_scrapers.parsers.bally_html.requests.get", _fake_get)

    result = parser.parse_listing(
        listing_html=listing_html,
        source_url="https://www.ballys.com/news/default.aspx",
        company_name="Bally's Interactive",
    )

    assert result.empty_reason is None
    assert result.candidate_urls == [
        "https://www.ballys.com/news-releases/news-release-details/ballys-interactive-announces-new-product-rollout"
    ]
    assert result.candidate_titles[result.candidate_urls[0]] == "Bally's Interactive Announces New Product Rollout"
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 24, 9, 0, 0)
