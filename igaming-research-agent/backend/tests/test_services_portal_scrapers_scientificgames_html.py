import datetime

from app.services.portal_scrapers.parsers.scientificgames_html import ScientificGamesHtmlParser


def test_scientificgames_parser_extracts_news_links_and_dates():
    parser = ScientificGamesHtmlParser()
    listing_html = """
    <a href='https://www.scientificgames.com/news/news-articles/a-modern-retail-story-driving-growth-in-the-uk/'>Mar 19, 2026 A Modern Retail Story: DRIVING GROWTH in the UK</a>
    <a href='https://www.scientificgames.com/news/media-releases/scientific-games-appoints-rich-wasserman-as-senior-vice-president-of-product-engineering/'>Feb 24, 2026 Scientific Games Appoints Rich Wasserman as Senior Vice President of Product Engineering</a>
    <a href='https://www.scientificgames.com/news/?p=2#pagination-result'>2</a>
    """

    result = parser.parse_listing(
        listing_html=listing_html,
        source_url="https://www.scientificgames.com/news/",
        company_name="Scientific Games",
    )

    assert result.empty_reason is None
    assert len(result.candidate_urls) == 2
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 19)
