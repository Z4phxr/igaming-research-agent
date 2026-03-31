from app.services.portal_scrapers.parsers.draftkings_html import DraftKingsHtmlParser


def test_draftkings_parser_extracts_candidates_from_h6_cards():
    parser = DraftKingsHtmlParser()
    listing_html = """
    <a href="/draftkings-debuts-predictions-app-entering-prediction-markets">
      <h6 class="css-1m1os8g">DraftKings Debuts Predictions App, Entering Prediction Markets</h6>
      <p class="css-1eaq9c6">New standalone mobile app applies DraftKings proven technology...</p>
    </a>
    <a href="/espn-and-draftkings-enter-multi-year-agreement">
      <h6 class="css-1m1os8g">ESPN and DraftKings Enter Multi-Year Agreement</h6>
    </a>
    <a href="/draftkings-about"><h6>About DraftKings</h6></a>
    """

    result = parser.parse_listing(listing_html, "https://www.draftkings.com/news-about", "DraftKings")

    assert result.empty_reason is None
    assert result.candidate_urls == [
        "https://www.draftkings.com/draftkings-debuts-predictions-app-entering-prediction-markets",
        "https://www.draftkings.com/espn-and-draftkings-enter-multi-year-agreement",
    ]
    assert (
        result.candidate_titles[
            "https://www.draftkings.com/draftkings-debuts-predictions-app-entering-prediction-markets"
        ]
        == "DraftKings Debuts Predictions App, Entering Prediction Markets"
    )


def test_draftkings_parser_extracts_candidates_from_markdown_links():
    parser = DraftKingsHtmlParser()
    listing_html = """
    [DraftKings Acquires Railbird to Advance Future Growth in Prediction Markets](https://www.draftkings.com/draftkings-acquires-railbird-to-advance-future-growth-in-prediction-markets)
    [DraftKings Set to Launch Mobile Sports Wagering in Missouri on December 1](https://www.draftkings.com/draftkings-set-to-launch-mobile-sports-wagering-in-missouri-on-december-1)
    [Who We Are](https://www.draftkings.com/who-we-are-about)
    """

    result = parser.parse_listing(listing_html, "https://www.draftkings.com/news-about", "DraftKings")

    assert result.empty_reason is None
    assert result.candidate_urls == [
        "https://www.draftkings.com/draftkings-acquires-railbird-to-advance-future-growth-in-prediction-markets",
        "https://www.draftkings.com/draftkings-set-to-launch-mobile-sports-wagering-in-missouri-on-december-1",
    ]
