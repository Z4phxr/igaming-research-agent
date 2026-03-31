import datetime

from app.services.portal_scrapers.parsers.rgc_html import RgcHtmlParser


def test_rgc_parser_extracts_items_from_embedded_rgc_content_json():
    parser = RgcHtmlParser()
    listing_html = """
    <script>
      var rgc_content = {"id":2,"articles":[
        {
          "heading":"Responsible Gambling Council Joins IGSA Responsible Gambling Committee as Partner Member",
          "date":"2026-03-12 09:00:24",
          "url":"https://responsiblegambling.org/about-rgc/rgc-news/responsible-gambling-council-joins-igsa-responsible-gambling-committee-as-partner-member/"
        },
        {
          "heading":"Second Post",
          "date":"2026-03-01 08:00:00",
          "url":"https://responsiblegambling.org/about-rgc/rgc-news/second-post/"
        }
      ]};
    </script>
    """

    result = parser.parse_listing(
        listing_html=listing_html,
        source_url="https://responsiblegambling.org/about-rgc/rgc-news/",
        company_name="Responsible Gambling Council",
    )

    assert result.empty_reason is None
    assert result.candidate_urls[0] == (
        "https://responsiblegambling.org/about-rgc/rgc-news/"
        "responsible-gambling-council-joins-igsa-responsible-gambling-committee-as-partner-member/"
    )
    assert result.candidate_titles[result.candidate_urls[0]] == (
        "Responsible Gambling Council Joins IGSA Responsible Gambling Committee as Partner Member"
    )
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 12, 9, 0, 24)
