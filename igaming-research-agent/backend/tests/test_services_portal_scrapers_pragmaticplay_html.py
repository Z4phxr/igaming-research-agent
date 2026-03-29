import datetime

from app.services.portal_scrapers.parsers.pragmaticplay_html import PragmaticPlayHtmlParser


def test_pragmaticplay_parser_extracts_news_links_and_dates():
    parser = PragmaticPlayHtmlParser()
    listing_html = """
    <article>
      <a href='/en/news/pragmatic-play-smart-studio-goes-live-with-cactus-gaming/'>PRAGMATIC PLAY'S SMART STUDIO GOES LIVE WITH CACTUS GAMING</a>
      <span>24th Mar 2026</span>
    </article>
    <article>
      <a href='/en/news/pragmatic-play-to-showcase-jelly-express-at-gat-cartagena/'>PRAGMATIC PLAY TO SHOWCASE JELLY EXPRESS AT GAT CARTAGENA</a>
      <span>18th Mar 2026</span>
    </article>
    """

    result = parser.parse_listing(
        listing_html=listing_html,
        source_url="https://www.pragmaticplay.com/en/news/",
        company_name="Pragmatic Play",
    )

    assert result.empty_reason is None
    assert len(result.candidate_urls) == 2
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 24)
