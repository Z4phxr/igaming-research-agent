import datetime

from app.services.portal_scrapers.parsers.caesars_html import CaesarsHtmlParser


def test_caesars_parser_extracts_links_titles_and_dates():
    parser = CaesarsHtmlParser()
    listing_html = """
    <div class='views-row'>
      Mar 23, 2026
      <a href='/news-releases/news-release-details/unique-boutique-and-unmistakably-lisa-vanderpump-vanderpump'>
        Unique, Boutique and Unmistakably Lisa Vanderpump
      </a>
    </div>
    <div class='views-row'>
      Mar 03, 2026
      <a href='/news-releases/news-release-details/caesars-race-sportsbook-officially-opens-resort-summerlin'>
        Caesars Race & Sportsbook Officially Opens at The Resort at Summerlin
      </a>
    </div>
    """

    result = parser.parse_listing(
        listing_html=listing_html,
        source_url="https://investor.caesars.com/press-releases",
        company_name="Caesars Sportsbook",
    )

    assert result.empty_reason is None
    assert result.candidate_urls == [
        "https://investor.caesars.com/news-releases/news-release-details/unique-boutique-and-unmistakably-lisa-vanderpump-vanderpump",
        "https://investor.caesars.com/news-releases/news-release-details/caesars-race-sportsbook-officially-opens-resort-summerlin",
    ]
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 23)
