import datetime

from app.services.portal_scrapers.parsers.fanatics_html import FanaticsHtmlParser


def test_fanatics_parser_extracts_release_links_titles_and_dates():
    parser = FanaticsHtmlParser()
    listing_html = """
    <article class='blog-basic-grid--container entry blog-item'>
      <span class='entry-date'>3/18/26</span>
      <h3>Meet Fran Campaign</h3>
      <a href='/press-releases/meet-fran-taraji'>Read More</a>
    </article>
    <article class='blog-basic-grid--container entry blog-item'>
      <span class='entry-date'>3/17/26</span>
      <h3>Cookin Up Parlays</h3>
      <a href='/press-releases/cookin-up-parlays'>Read More</a>
    </article>
    """

    result = parser.parse_listing(
        listing_html=listing_html,
        source_url="https://www.fanaticsinc.com/press-releases",
        company_name="Fanatics Sportsbook",
    )

    assert result.empty_reason is None
    assert result.candidate_urls == [
        "https://www.fanaticsinc.com/press-releases/meet-fran-taraji",
        "https://www.fanaticsinc.com/press-releases/cookin-up-parlays",
    ]
    assert result.candidate_titles[result.candidate_urls[0]] == "Meet Fran Campaign"
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 18)


def test_fanatics_parser_extracts_article_published_date_from_json_ld():
    parser = FanaticsHtmlParser()
    article_html = '<script type="application/ld+json">{"datePublished":"2026-03-18T09:45:01-0700"}</script>'

    parsed = parser.extract_article_published_date(article_html)

    assert parsed is not None
    assert parsed == datetime.datetime(2026, 3, 18, 16, 45, 1)
