import datetime

from app.services.portal_scrapers.parsers.illinois_igb_html import IllinoisIgbHtmlParser


def test_illinois_igb_parser_extracts_press_release_links_from_rendered_anchors():
    parser = IllinoisIgbHtmlParser()
    listing_html = """
    <div class="cmp-news-feed__text">
      <p><strong><a href="https://www.illinois.gov/news/press-release.32173.html">Illinois Gaming Board and Attorney General's Office Issue more than 60 Cease-and-Desist Letters</a></strong></p>
    </div>
    <div class="cmp-news-feed__text">
      <p><strong><a href="/news/press-release.32003.html">IGB Previews Par-A-Dice Hotel Casino's Redevelopment Proposal During Final 2025 Meeting</a></strong></p>
    </div>
    """

    result = parser.parse_listing(
        listing_html=listing_html,
        source_url="https://igb.illinois.gov/news/press-releases.html",
        company_name="Illinois Gaming Board",
    )

    assert result.empty_reason is None
    assert result.candidate_urls == [
        "https://www.illinois.gov/news/press-release.32173.html",
        "https://igb.illinois.gov/news/press-release.32003.html",
    ]


def test_illinois_igb_parser_handles_dynamic_template_with_no_materialized_urls():
    parser = IllinoisIgbHtmlParser()
    listing_html = """
    <script id="news-feed-template-id-1" type="text/x-handlebars-template">
      <a href="{{this.url}}">{{this.title}}</a>
    </script>
    <div class="cmp-news-feed" data-news-feed-url="/content/soi/igb/en/news/press-releases/jcr:content/responsivegrid/container/news_feed.model.json"></div>
    """

    result = parser.parse_listing(
        listing_html=listing_html,
        source_url="https://igb.illinois.gov/news/press-releases.html",
        company_name="Illinois Gaming Board",
    )

    assert result.candidate_urls == []
    assert result.empty_reason == "dynamic_listing_no_static_links"


def test_illinois_igb_parser_extracts_release_links_from_escaped_model_json_payload():
    parser = IllinoisIgbHtmlParser()
    listing_html = (
        '{"newsFeedItemList":['
        '{"url":"\\/news\\/press-release.32173.html"},'
        '{"url":"\\/news\\/press-release.32003.html"},'
        '{"url":"\\/content\\/dam\\/soi\\/en\\/web\\/igb\\/documents\\/press-releases\\/additional-news\\/state-of-illinois-recognizes-march-as-problem-gambling-awareness-month.pdf"}'
        ']}'
    )

    result = parser.parse_listing(
        listing_html=listing_html,
        source_url="https://igb.illinois.gov/news/press-releases.html",
        company_name="Illinois Gaming Board",
    )

    assert result.empty_reason is None
    assert result.candidate_urls == [
        "https://igb.illinois.gov/news/press-release.32173.html",
        "https://igb.illinois.gov/news/press-release.32003.html",
        "https://igb.illinois.gov/content/dam/soi/en/web/igb/documents/press-releases/additional-news/state-of-illinois-recognizes-march-as-problem-gambling-awareness-month.pdf",
    ]


def test_illinois_igb_extracts_article_date_from_page_text():
    parser = IllinoisIgbHtmlParser()
    article_html = "<div>Wednesday, February 04, 2026</div>"

    parsed = parser.extract_article_published_date(article_html)

    assert parsed == datetime.datetime(2026, 2, 4)
