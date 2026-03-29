import datetime

from app.services.portal_scrapers.parsers.evolution_html import EvolutionHtmlParser


def test_evolution_parser_extracts_cards_with_url_title_and_date():
    parser = EvolutionHtmlParser()
    html = '''
    <a href="https://www.evolution.com/news/evolution-launches-crazy-time-brasil/" class="news-card mb-5 col-12">
        <span class="news-card-date">18/03/26</span>
        <div class="news-card-content mt-4">
            <p class="h4">Evolution launches Crazy Time Brasil</p>
        </div>
    </a>
    '''

    cutoff = datetime.datetime(2026, 3, 1)
    now = datetime.datetime(2026, 3, 29)
    result = parser.parse_listing(html, "https://www.evolution.com/news", "Evolution Gaming", cutoff=cutoff, now_utc=now)

    assert result.empty_reason is None
    assert result.candidate_urls == ["https://www.evolution.com/news/evolution-launches-crazy-time-brasil/"]
    assert result.candidate_titles[result.candidate_urls[0]] == "Evolution launches Crazy Time Brasil"
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 18)


def test_evolution_parser_returns_empty_when_first_card_is_outside_window():
    parser = EvolutionHtmlParser()
    html = '''
    <a href="https://www.evolution.com/news/older/" class="news-card mb-5 col-12">
        <span class="news-card-date">10/01/26</span>
        <p class="h4">Old release</p>
    </a>
    <a href="https://www.evolution.com/news/newer/" class="news-card mb-5 col-12">
        <span class="news-card-date">18/03/26</span>
        <p class="h4">Should not be considered when first is stale</p>
    </a>
    '''

    cutoff = datetime.datetime(2026, 3, 15)
    now = datetime.datetime(2026, 3, 29)
    result = parser.parse_listing(html, "https://www.evolution.com/news", "Evolution Gaming", cutoff=cutoff, now_utc=now)

    assert result.candidate_urls == []
    assert result.empty_reason == "listing_first_card_outside_time_window"


def test_evolution_parser_stops_after_first_stale_following_new_items():
    parser = EvolutionHtmlParser()
    html = '''
    <a href="https://www.evolution.com/news/new-1/" class="news-card mb-5 col-12">
        <span class="news-card-date">20/03/26</span>
        <p class="h4">New 1</p>
    </a>
    <a href="https://www.evolution.com/news/new-2/" class="news-card mb-5 col-12">
        <span class="news-card-date">19/03/26</span>
        <p class="h4">New 2</p>
    </a>
    <a href="https://www.evolution.com/news/old/" class="news-card mb-5 col-12">
        <span class="news-card-date">10/03/26</span>
        <p class="h4">Old</p>
    </a>
    <a href="https://www.evolution.com/news/new-but-later-in-dom/" class="news-card mb-5 col-12">
        <span class="news-card-date">18/03/26</span>
        <p class="h4">Should not be parsed after stale break</p>
    </a>
    '''

    cutoff = datetime.datetime(2026, 3, 15)
    now = datetime.datetime(2026, 3, 29)
    result = parser.parse_listing(html, "https://www.evolution.com/news", "Evolution Gaming", cutoff=cutoff, now_utc=now)

    assert result.candidate_urls == [
        "https://www.evolution.com/news/new-1/",
        "https://www.evolution.com/news/new-2/",
    ]
