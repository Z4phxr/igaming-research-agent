import datetime

from app.services.portal_scrapers.parsers.penn_html import PennHtmlParser


def test_penn_parser_extracts_links_titles_and_dates():
    parser = PennHtmlParser()
    listing_html = """
    <div class='news-item'>
      March 19, 2026
      <a href='/news-releases/news-release-details/penn-entertainment-sets-june-24-grand-opening-date-new-hollywood'>
        PENN Entertainment Sets June 24 as Grand Opening Date for New Hollywood Casino Aurora in Illinois
      </a>
    </div>
    <div class='news-item'>
      March 12, 2026
      <a href='/news-releases/news-release-details/penn-entertainment-sets-june-12-grand-opening-date-new-hotel'>
        PENN Entertainment Sets June 12 as Grand Opening Date for New Hotel at Hollywood Casino Columbus
      </a>
    </div>
    """

    result = parser.parse_listing(
        listing_html=listing_html,
        source_url="https://investors.pennentertainment.com/press-releases",
        company_name="ESPN Bet / PENN Entertainment",
    )

    assert result.empty_reason is None
    assert result.candidate_urls == [
        "https://investors.pennentertainment.com/news-releases/news-release-details/penn-entertainment-sets-june-24-grand-opening-date-new-hollywood",
        "https://investors.pennentertainment.com/news-releases/news-release-details/penn-entertainment-sets-june-12-grand-opening-date-new-hotel",
    ]
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 19)
