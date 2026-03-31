import datetime
from unittest.mock import Mock, patch

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


@patch("app.services.portal_scrapers.parsers.bettercollective_html.requests.get")
def test_bettercollective_parser_extracts_dynamic_mfn_feed(mock_get):
    parser = BetterCollectiveHtmlParser()
    listing_html = """
    <html>
      <head>
        <script>
          window._MFN = {
            "feed_id": "d06588d3-6254-497f-9f5a-bdb6338491ea",
            "single_view_url": "/press-releases/"
          };
        </script>
      </head>
      <body></body>
    </html>
    """

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "items": [
            {
                "content": {
                    "title": "Better Collective expands into prediction markets",
                    "slug": "better-collective-expands-into-prediction-markets",
                    "publish_date": "2026-03-19T13:30:00Z",
                }
            }
        ]
    }
    mock_get.return_value = response

    result = parser.parse_listing(listing_html, "https://bettercollective.com/press-releases/", "Better Collective")

    assert result.empty_reason is None
    assert result.candidate_urls == [
        "https://bettercollective.com/press-releases/?slug=better-collective-expands-into-prediction-markets"
    ]
    assert result.candidate_titles[result.candidate_urls[0]] == "Better Collective expands into prediction markets"
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 19, 13, 30)


@patch("app.services.portal_scrapers.parsers.bettercollective_html.requests.get")
def test_bettercollective_parser_extracts_dynamic_mfn_feed_from_loader_script(mock_get):
    parser = BetterCollectiveHtmlParser()
    listing_html = """
    <html>
      <head>
        <script src="https://bettercollective.com/wp-content/plugins/bc-news-landing-page/includes/mfn-loader-news-landing-page.js?v=1"></script>
      </head>
      <body></body>
    </html>
    """

    loader_response = Mock()
    loader_response.raise_for_status.return_value = None
    loader_response.text = "window._MFN = {\"feed_id\": \"d06588d3-6254-497f-9f5a-bdb6338491ea\", \"single_view_url\": \"/press-releases/\"};"

    feed_response = Mock()
    feed_response.raise_for_status.return_value = None
    feed_response.json.return_value = {
        "items": [
            {
                "content": {
                    "title": "Amendment of share buyback program",
                    "slug": "amendment-of-share-buyback-program",
                    "publish_date": "2026-03-24T16:40:00Z",
                }
            }
        ]
    }

    mock_get.side_effect = [loader_response, feed_response]

    result = parser.parse_listing(listing_html, "https://bettercollective.com/press-releases/", "Better Collective")

    assert result.empty_reason is None
    assert result.candidate_urls == [
        "https://bettercollective.com/press-releases/?slug=amendment-of-share-buyback-program"
    ]


@patch("app.services.portal_scrapers.parsers.bettercollective_html.requests.get")
def test_bettercollective_parser_does_not_false_flag_cloudflare_when_dynamic_data_exists(mock_get):
    parser = BetterCollectiveHtmlParser()
    listing_html = """
    <html>
      <head>
        <script>
          window._MFN = {"feed_id": "d06588d3-6254-497f-9f5a-bdb6338491ea"};
        </script>
      </head>
      <body>
        <div>cloudflare</div>
      </body>
    </html>
    """

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "items": [
            {
                "content": {
                    "title": "Annual General Meeting in Better Collective",
                    "slug": "annual-general-meeting-in-better-collective-3",
                    "publish_date": "2026-03-24T11:45:00Z",
                }
            }
        ]
    }
    mock_get.return_value = response

    result = parser.parse_listing(listing_html, "https://bettercollective.com/press-releases/", "Better Collective")

    assert result.empty_reason is None
    assert len(result.candidate_urls) == 1


def test_bettercollective_parser_marks_true_block_pages():
    parser = BetterCollectiveHtmlParser()
    blocked_html = """
    <html>
      <head><title>Attention Required</title></head>
      <body>
        <div>cf-chl-bypass</div>
        <h1>Access denied</h1>
      </body>
    </html>
    """

    result = parser.parse_listing(blocked_html, "https://bettercollective.com/press-releases/", "Better Collective")

    assert result.candidate_urls == []
    assert result.empty_reason == "bot_protection_blocked"
