import datetime

from app.services.portal_scrapers.parsers.hardrock_html import HardRockHtmlParser


def test_hardrock_parser_extracts_links_titles_and_dates_from_news_cards():
    parser = HardRockHtmlParser()
    listing_html = """
    <div class='cfcards news-cf cmp-button--primary'>
      <h3>Hard Rock Hotel Malta Now Accepting Bookings</h3>
      <p>March 24, 2026</p>
      <a href='/blog/hard-rock-hotel-malta-now-accepting-bookings-summer-2026-debut'>Read more</a>
    </div>
    <div class='cfcards news-cf cmp-button--primary'>
      <h3>Hard Rock Heals Foundation Donates</h3>
      <p>March 20, 2026</p>
      <a href='/blog/hard-rock-heals-foundation-donates-jamaica-hurricane-relief'>Read more</a>
    </div>
    """

    result = parser.parse_listing(
        listing_html=listing_html,
        source_url="https://www.hardrock.com/blog",
        company_name="Hard Rock Bet",
    )

    assert result.empty_reason is None
    assert result.candidate_urls == [
        "https://www.hardrock.com/blog/hard-rock-hotel-malta-now-accepting-bookings-summer-2026-debut",
        "https://www.hardrock.com/blog/hard-rock-heals-foundation-donates-jamaica-hurricane-relief",
    ]
    assert result.candidate_titles[result.candidate_urls[0]] == "Hard Rock Hotel Malta Now Accepting Bookings"
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 24)


def test_hardrock_parser_filters_results_pages():
    parser = HardRockHtmlParser()
    listing_html = """
    <a href='/blog/results.page.2?keyword='>Older Posts</a>
    <a href='/blog/results.category.page.1?keyword=shrss:news-categories/press-releases'>Press Releases</a>
    <a href='/blog/new-leadership-appointments-seminole-gaming-hard-rock-international'>Seminole Gaming and Hard Rock International Announce New Leadership Appointments</a>
    """

    result = parser.parse_listing(
        listing_html=listing_html,
        source_url="https://www.hardrock.com/blog",
        company_name="Hard Rock Bet",
    )

    assert result.candidate_urls == [
        "https://www.hardrock.com/blog/new-leadership-appointments-seminole-gaming-hard-rock-international"
    ]
