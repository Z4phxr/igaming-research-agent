import datetime

from app.services.portal_scrapers.parsers.sportradar_html import SportradarHtmlParser


def test_sportradar_parser_extracts_content_hub_news_links():
    parser = SportradarHtmlParser()
    listing_html = """
    <a href='https://sportradar.com/content-hub/news/sportradar-expands-partnership-with-hard-rock-bet-adding-official-data-from-the-pga-tour-and-ultimate-fighting-championship/'>Sportradar Expands Partnership with Hard Rock Bet</a>
    <span>26 March 2026</span>
    <a href='https://sportradar.com/content-hub/news/sportradar-launches-igaming-brand-playradar-combining-sports-data-expertise-with-casino-content-for-global-operators/'>Sportradar launches iGaming brand Playradar</a>
    <span>24 March 2026</span>
    """

    result = parser.parse_listing(listing_html, "https://sportradar.com/content-hub/", "Sportradar")

    assert result.empty_reason is None
    assert len(result.candidate_urls) == 2
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 26)
