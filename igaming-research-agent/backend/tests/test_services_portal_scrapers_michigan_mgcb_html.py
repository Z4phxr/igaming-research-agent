import datetime

from app.services.portal_scrapers.parsers.michigan_mgcb_html import MichiganMgcbHtmlParser


def test_michigan_mgcb_parser_extracts_listing_links_and_titles_from_cards():
    parser = MichiganMgcbHtmlParser()
    listing_html = """
    <div class="com-wrapper">
      <div class="row">
        <div class="col-12 col-md-8">
          <div class="related-content__section-content">
            <a href="/mgcb/news/2026/03/17/february-2026-igaming-revenue">
              <h3>Michigan iGaming, online sports betting operators report $313M in February revenue</h3>
            </a>
          </div>
        </div>
      </div>
    </div>
    <div class="com-wrapper">
      <div class="row">
        <div class="col-12 col-md-8">
          <div class="related-content__section-content">
            <a href="/mgcb/news/2026/03/17/mgcb-launches-expanded-website">
              <h3>Michigan Gaming Control Board launches expanded website with new resources to support responsible gaming</h3>
            </a>
          </div>
        </div>
      </div>
    </div>
    """

    result = parser.parse_listing(
        listing_html=listing_html,
        source_url="https://www.michigan.gov/mgcb/news",
        company_name="Michigan Gaming Control Board",
    )

    assert result.empty_reason is None
    assert result.candidate_urls == [
        "https://www.michigan.gov/mgcb/news/2026/03/17/february-2026-igaming-revenue",
        "https://www.michigan.gov/mgcb/news/2026/03/17/mgcb-launches-expanded-website",
    ]


def test_michigan_mgcb_parser_extracts_article_date_from_meta_datepublished():
    parser = MichiganMgcbHtmlParser()
    article_html = '<meta name="datePublished" content="03/10/2026 12:00:00" />'

    parsed = parser.extract_article_published_date(article_html)

    assert parsed == datetime.datetime(2026, 3, 10, 12, 0, 0)
