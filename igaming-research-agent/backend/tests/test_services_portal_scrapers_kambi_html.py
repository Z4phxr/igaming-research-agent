import datetime

from app.services.portal_scrapers.parsers.kambi_html import KambiHtmlParser


def test_kambi_parser_extracts_news_insight_links_and_dates():
    parser = KambiHtmlParser()
    listing_html = """
    <article>
      <a href='https://www.kambi.com/news-insights/tribal-sports-betting-report-2026/'>Tribes see growing sports betting activity as SGP and live betting adoption continue to rise, Kambi's 2026 Report finds</a>
      <div>23. 02 2026</div>
    </article>
    <article>
      <a href='https://www.kambi.com/news-insights/mandan-hidatsa-and-arikara-nation-sports-betting-north-dakota/'>Kambi Group plc partners with the Mandan, Hidatsa and Arikara Nation</a>
      <div>16. 02 2026</div>
    </article>
    """

    result = parser.parse_listing(
        listing_html=listing_html,
        source_url="https://www.kambi.com/news-insights/",
        company_name="Kambi",
    )

    assert result.empty_reason is None
    assert len(result.candidate_urls) == 2
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 2, 23)
