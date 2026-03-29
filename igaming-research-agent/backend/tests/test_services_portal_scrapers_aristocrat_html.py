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


def test_aristocrat_parser_uses_headline_link_when_thumbnail_anchor_is_first():
    parser = AristocratHtmlParser()
    listing_html = """
    <article class='anim-fade-in-up'>
      <a href='/thumbnail-target/'><img src='/thumb.jpg' alt='thumb'></a>
      <h2 class='h4 entry-title my-0'>
        <a href='/real-news-item/'>Real News Item Title</a>
      </h2>
      <div class='post-date text-end'>
        <time datetime='2026-03-29T14:27:21+11:00'>Mar 29, 2026</time>
      </div>
    </article>
    """

    result = parser.parse_listing(listing_html, "https://www.aristocrat.com/news/", "Aristocrat Leisure")

    assert result.empty_reason is None
    assert result.candidate_urls == ["https://www.aristocrat.com/real-news-item/"]
    assert result.candidate_titles[result.candidate_urls[0]] == "Real News Item Title"
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 29, 3, 27, 21)
