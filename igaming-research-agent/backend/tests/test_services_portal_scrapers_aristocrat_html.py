import datetime

from app.services.portal_scrapers.parsers.aristocrat_html import AristocratHtmlParser


def test_aristocrat_parser_extracts_article_links_and_dates():
    parser = AristocratHtmlParser()
    listing_html = """
    <article>
      <a href='/aristocrat-announces-the-acquisition-of-gaming-analytics-inc/'>Aristocrat announces the acquisition of Gaming Analytics, Inc</a>
      <time>Feb 11, 2026</time>
    </article>
    <article>
      <a href='/aristocrat-announces-new-executive-leadership-appointments-for-technology-and-the-emea-region/'>Aristocrat Announces New Executive Leadership Appointments for Technology and the EMEA region</a>
      <time>Feb 6, 2026</time>
    </article>
    """

    result = parser.parse_listing(listing_html, "https://www.aristocrat.com/news/", "Aristocrat Leisure")

    assert result.empty_reason is None
    assert result.candidate_urls[0] == "https://www.aristocrat.com/aristocrat-announces-the-acquisition-of-gaming-analytics-inc/"
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 2, 11)
