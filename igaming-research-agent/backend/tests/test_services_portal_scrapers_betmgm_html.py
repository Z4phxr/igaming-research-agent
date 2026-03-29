import datetime

from app.services.portal_scrapers.parsers.betmgm_html import BetMgmHtmlParser


def test_betmgm_parser_extracts_tiles_with_url_title_and_date():
    parser = BetMgmHtmlParser()
    html = '''
        <div class="section-intro"><h2>Latest Stories</h2></div>
        <div id="sf-posts">
    <div class="news-tile long-news-tile -tag news-tile-392227">
      <h3><a href="https://sports.betmgm.com/en/blog/betmgm-st-louis-blues-announce-official-sports-betting-partnership/">
        BetMGM and St. Louis Blues Announce Official Sports Betting Partnership
      </a></h3>
      <span class="tile-date">Jan 20, 2026</span>
    </div>
        </div>
    '''

    cutoff = datetime.datetime(2026, 1, 1)
    now = datetime.datetime(2026, 3, 29)
    result = parser.parse_listing(html, "https://sports.betmgm.com/en/blog", "BetMGM", cutoff=cutoff, now_utc=now)

    assert result.empty_reason is None
    assert len(result.candidate_urls) == 1
    assert result.candidate_urls[0] == (
        "https://sports.betmgm.com/en/blog/betmgm-st-louis-blues-announce-official-sports-betting-partnership/"
    )
    assert result.candidate_titles[result.candidate_urls[0]] == (
        "BetMGM and St. Louis Blues Announce Official Sports Betting Partnership"
    )
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 1, 20)


def test_betmgm_parser_returns_empty_when_first_tile_is_outside_window():
    parser = BetMgmHtmlParser()
    html = '''
    <div class="section-intro"><h2>Latest Stories</h2></div>
    <div id="sf-posts">
    <div class="news-tile long-news-tile"><h3><a href="/old">Old</a></h3><span class="tile-date">Jan 10, 2026</span></div>
    <div class="news-tile long-news-tile"><h3><a href="/new">New</a></h3><span class="tile-date">Mar 20, 2026</span></div>
    </div>
    '''

    cutoff = datetime.datetime(2026, 3, 15)
    now = datetime.datetime(2026, 3, 29)
    result = parser.parse_listing(html, "https://sports.betmgm.com/en/blog", "BetMGM", cutoff=cutoff, now_utc=now)

    assert result.candidate_urls == []
    assert result.empty_reason == "listing_first_tile_outside_time_window"


def test_betmgm_parser_stops_after_first_stale_following_new_items():
    parser = BetMgmHtmlParser()
    html = '''
    <div class="section-intro"><h2>Latest Stories</h2></div>
    <div id="sf-posts">
    <div class="news-tile long-news-tile"><h3><a href="/new-1">New 1</a></h3><span class="tile-date">Mar 25, 2026</span></div>
    <div class="news-tile long-news-tile"><h3><a href="/new-2">New 2</a></h3><span class="tile-date">Mar 24, 2026</span></div>
    <div class="news-tile long-news-tile"><h3><a href="/old-1">Old 1</a></h3><span class="tile-date">Mar 10, 2026</span></div>
    <div class="news-tile long-news-tile"><h3><a href="/should-not-parse">Skip</a></h3><span class="tile-date">Mar 20, 2026</span></div>
    </div>
    '''

    cutoff = datetime.datetime(2026, 3, 15)
    now = datetime.datetime(2026, 3, 29)
    result = parser.parse_listing(html, "https://sports.betmgm.com/en/blog", "BetMGM", cutoff=cutoff, now_utc=now)

    assert result.candidate_urls == [
        "https://sports.betmgm.com/new-1",
        "https://sports.betmgm.com/new-2",
    ]


def test_betmgm_parser_date_parsing():
    parser = BetMgmHtmlParser()

    assert parser._parse_tile_date("Jan 20, 2026") == datetime.datetime(2026, 1, 20)
    assert parser._parse_tile_date("Dec 31, 2025") == datetime.datetime(2025, 12, 31)
    assert parser._parse_tile_date("Invalid") is None
    assert parser._parse_tile_date("") is None


def test_betmgm_parser_ignores_tiles_before_latest_stories():
    parser = BetMgmHtmlParser()
    html = '''
    <div class="news-tile long-news-tile"><h3><a href="/featured">Featured tile</a></h3><span class="tile-date">Mar 29, 2026</span></div>
    <div class="section-intro"><h2>Latest Stories</h2></div>
    <div id="sf-posts">
      <div class="news-tile long-news-tile"><h3><a href="/latest-1">Latest 1</a></h3><span class="tile-date">Mar 28, 2026</span></div>
      <div class="news-tile long-news-tile"><h3><a href="/latest-2">Latest 2</a></h3><span class="tile-date">Mar 27, 2026</span></div>
    </div>
    '''

    cutoff = datetime.datetime(2026, 3, 1)
    now = datetime.datetime(2026, 3, 29)
    result = parser.parse_listing(html, "https://sports.betmgm.com/en/blog", "BetMGM", cutoff=cutoff, now_utc=now)

    assert result.candidate_urls == [
        "https://sports.betmgm.com/latest-1",
        "https://sports.betmgm.com/latest-2",
    ]


def test_betmgm_parser_returns_reason_when_latest_stories_missing():
    parser = BetMgmHtmlParser()
    html = '<div class="news-tile long-news-tile"><h3><a href="/x">X</a></h3><span class="tile-date">Mar 20, 2026</span></div>'

    result = parser.parse_listing(html, "https://sports.betmgm.com/en/blog", "BetMGM")

    assert result.candidate_urls == []
    assert result.empty_reason == "no_latest_stories_section"
