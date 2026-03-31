import datetime

from app.services.portal_scrapers.parsers.config_driven_html import ConfigDrivenHtmlParser, HtmlListingParserConfig


def _build_parser() -> ConfigDrivenHtmlParser:
    return ConfigDrivenHtmlParser(
        [
            HtmlListingParserConfig(
                name="test-config",
                source_url_contains=("config-driven.example",),
                item_selector="article.release-item",
                link_selector="a[href]",
                title_selector="h2",
                date_selector="time",
                date_formats=("%Y-%m-%d",),
                descending_chronological=True,
            )
        ]
    )


def test_config_driven_parser_extracts_urls_titles_and_dates():
    parser = _build_parser()
    html = """
    <section>
      <article class='release-item'>
        <h2>First Release</h2>
        <a href='/press/first'>Open</a>
        <time>2026-03-20</time>
      </article>
      <article class='release-item'>
        <h2>Second Release</h2>
        <a href='/press/second'>Open</a>
        <time>2026-03-18</time>
      </article>
    </section>
    """

    result = parser.parse_listing(
        listing_html=html,
        source_url="https://config-driven.example/news",
        company_name="Example",
        cutoff=datetime.datetime(2026, 3, 1),
        now_utc=datetime.datetime(2026, 3, 29),
    )

    assert result.empty_reason is None
    assert result.candidate_urls == [
        "https://config-driven.example/press/first",
        "https://config-driven.example/press/second",
    ]
    assert result.candidate_titles[result.candidate_urls[0]] == "First Release"
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 20)


def test_config_driven_parser_stops_on_stale_when_descending():
    parser = _build_parser()
    html = """
    <article class='release-item'><h2>Fresh</h2><a href='/fresh'>Fresh</a><time>2026-03-21</time></article>
    <article class='release-item'><h2>Stale</h2><a href='/stale'>Stale</a><time>2026-02-01</time></article>
    <article class='release-item'><h2>Should Not Parse</h2><a href='/skip'>Skip</a><time>2026-03-22</time></article>
    """

    result = parser.parse_listing(
        listing_html=html,
        source_url="https://config-driven.example/news",
        company_name="Example",
        cutoff=datetime.datetime(2026, 3, 1),
        now_utc=datetime.datetime(2026, 3, 29),
    )

    assert result.candidate_urls == ["https://config-driven.example/fresh"]


def test_config_driven_parser_returns_no_matching_config_for_unknown_source():
    parser = _build_parser()

    result = parser.parse_listing(
        listing_html="<article class='release-item'><a href='/x'>X</a></article>",
        source_url="https://unknown.example/news",
        company_name="Unknown",
    )

    assert result.candidate_urls == []
    assert result.empty_reason == "no_matching_config"
