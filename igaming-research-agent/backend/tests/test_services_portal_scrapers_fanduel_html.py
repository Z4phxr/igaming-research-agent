import datetime

from app.services.portal_scrapers.parsers.fanduel_html import FanDuelHtmlParser


def test_fanduel_parser_extracts_news_links_and_skips_non_article_routes():
    parser = FanDuelHtmlParser()
    html = """
    <a class='ArticlePreviewLink_article__fkeM_' href='/about/news/fanduel-picks-platform-to-sunset'>
      <h3>FanDuel Picks Platform to Sunset</h3>
    </a>
    <a class='ArticlePreviewLink_article__fkeM_' href='/about/news/company-news/all'>
      <h3>Company News</h3>
    </a>
    <a class='ArticlePreviewLink_article__fkeM_' href='/about/news/problem-gambling-support-and-resources'>
      <h3>Problem Gambling Support and Resources</h3>
    </a>
    <a class='ArticlePreviewLink_article__fkeM_' href='/about/news/faqs'>
      <h3>FAQs</h3>
    </a>
    """

    result = parser.parse_listing(
        listing_html=html,
        source_url="https://www.fanduel.com/about/news",
        company_name="FanDuel",
    )

    assert result.empty_reason is None
    assert result.candidate_urls == [
        "https://www.fanduel.com/about/news/fanduel-picks-platform-to-sunset",
        "https://www.fanduel.com/about/news/problem-gambling-support-and-resources",
    ]
    assert result.candidate_titles[result.candidate_urls[0]] == "FanDuel Picks Platform to Sunset"


def test_fanduel_parser_extracts_article_published_date():
    parser = FanDuelHtmlParser()
    article_html = '<meta property="article:published_time" content="2026-03-27T00:00:00.000Z" />'

    parsed = parser.extract_article_published_date(article_html)

    assert parsed is not None
    assert parsed == datetime.datetime(2026, 3, 27, 0, 0, 0)
