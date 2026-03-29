import datetime

from app.services.portal_scrapers.registry import resolve_listing_parser


def test_pa_config_extracts_press_release_links():
    parser = resolve_listing_parser(
        "https://gamingcontrolboard.pa.gov/news-and-transparency/press-release",
        "Pennsylvania Gaming Control Board",
    )
    assert parser is not None

    html = """
    <section>
      <a href="/news-and-transparency/press-release/pa-gaming-control-board-fines-betmgm-100000">
        Read the complete press release here
      </a>
      <a href="/news-and-transparency/press-release?page=2">Next page</a>
    </section>
    """

    result = parser.parse_listing(
        listing_html=html,
        source_url="https://gamingcontrolboard.pa.gov/news-and-transparency/press-release",
        company_name="Pennsylvania Gaming Control Board",
        cutoff=datetime.datetime(2026, 3, 1),
        now_utc=datetime.datetime(2026, 3, 29),
    )

    assert result.candidate_urls == [
        "https://gamingcontrolboard.pa.gov/news-and-transparency/press-release/pa-gaming-control-board-fines-betmgm-100000"
    ]


def test_nj_dge_config_extracts_press_release_pdfs_from_table_rows():
    parser = resolve_listing_parser(
        "https://www.njoag.gov/about/divisions-and-offices/division-of-gaming-enforcement-home/news-and-updates/",
        "New Jersey DGE",
    )
    assert parser is not None

    html = """
    <table>
      <tbody>
        <tr>
          <td valign='top'><img src='https://www.nj.gov/oag/ge/images/arrow.gif' alt='' /></td>
          <td>03/16/26 - <a href='https://www.nj.gov/oag/ge/docs/Financials/PressRelease2026/February2026.pdf'>DGE Announces February 2026 Press Release</a></td>
        </tr>
        <tr>
          <td valign='top'><img src='https://www.nj.gov/oag/ge/images/arrow.gif' alt='' /></td>
          <td>02/17/26 - <a href='https://www.nj.gov/oag/ge/docs/Financials/PressRelease2026/January2026.pdf'>DGE Announces January 2026 Press Release</a></td>
        </tr>
      </tbody>
    </table>
    """

    result = parser.parse_listing(
        listing_html=html,
        source_url="https://www.njoag.gov/about/divisions-and-offices/division-of-gaming-enforcement-home/news-and-updates/",
        company_name="New Jersey DGE",
    )

    assert result.empty_reason is None
    assert result.candidate_urls == [
        "https://www.nj.gov/oag/ge/docs/Financials/PressRelease2026/February2026.pdf",
        "https://www.nj.gov/oag/ge/docs/Financials/PressRelease2026/January2026.pdf",
    ]


def test_nigc_config_extracts_download_links():
    parser = resolve_listing_parser("https://www.nigc.gov/downloads/news/", "National Indian Gaming Commission")
    assert parser is not None

    html = """
    <h2>
      <a href="https://www.nigc.gov/download/nigc-releases-notice-of-inquiry-and-announces-regulatory-review-consultation-dates/">
        NIGC Releases Notice of Inquiry
      </a>
    </h2>
    """

    result = parser.parse_listing(
        listing_html=html,
        source_url="https://www.nigc.gov/downloads/news/",
        company_name="National Indian Gaming Commission",
    )

    assert result.candidate_urls == [
        "https://www.nigc.gov/download/nigc-releases-notice-of-inquiry-and-announces-regulatory-review-consultation-dates/"
    ]


def test_sba_config_filters_nav_links_and_keeps_latest_story_links():
    parser = resolve_listing_parser("https://sportsbettingalliance.org/about/", "Sports Betting Alliance")
    assert parser is not None

    html = """
    <div class="et_pb_text_inner"><h2>THE LATEST</h2></div>
    <div class="post_types post_types_0">
      <div class="post-types-container slider">
        <div class="lwp_post_carousel_item">
          <h4 class="lwp_post_carousel_heading">
            <a class="lwp_post_title" href="https://sportsbettingalliance.org/fanduel-introduces-play-with-a-plan-a-research-based-approach-to-responsible-gaming/">
              FanDuel Introduces "Play with a Plan"
            </a>
          </h4>
          <p class="lwp_post_carousel_meta"><span class="lwp_meta_date">Jan 22, 2026</span></p>
        </div>
        <div class="lwp_post_carousel_item">
          <h4 class="lwp_post_carousel_heading">
            <a class="lwp_post_title" href="https://sportsbettingalliance.org/draftkings-adds-another-brick-in-its-rg-wall-with-evive-integration/">
              DraftKings adds another brick in its RG wall with Evive integration
            </a>
          </h4>
          <p class="lwp_post_carousel_meta"><span class="lwp_meta_date">Oct 3, 2025</span></p>
        </div>
      </div>
    </div>
    <nav>
      <a href="https://sportsbettingalliance.org/about/">About</a>
      <a href="https://sportsbettingalliance.org/privacy-policy/">Privacy Policy</a>
      <a href="https://sportsbettingalliance.org/random-unscoped-link/">Random Unscoped Link</a>
    </nav>
    """

    result = parser.parse_listing(
        listing_html=html,
        source_url="https://sportsbettingalliance.org/about/",
        company_name="Sports Betting Alliance",
    )

    assert result.candidate_urls == [
        "https://sportsbettingalliance.org/fanduel-introduces-play-with-a-plan-a-research-based-approach-to-responsible-gaming/",
        "https://sportsbettingalliance.org/draftkings-adds-another-brick-in-its-rg-wall-with-evive-integration/",
    ]
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 1, 22)


def test_wv_config_sets_blocked_reason_for_forbidden_page():
    parser = resolve_listing_parser(
        "https://wvlottery.com/news-and-winning/news-and-offers/news-and-events",
        "West Virginia Lottery",
    )
    assert parser is not None

    result = parser.parse_listing(
        listing_html="<html><body><h1>403 Forbidden</h1></body></html>",
        source_url="https://wvlottery.com/news-and-winning/news-and-offers/news-and-events",
        company_name="West Virginia Lottery",
    )

    assert result.candidate_urls == []
    assert result.empty_reason == "bot_protection_blocked"


def test_rgc_config_matches_company_name_and_extracts_news_links():
    parser = resolve_listing_parser("https://responsiblegambling.org/about-rgc/rgc-news/", "Responsible Gambling Council")
    assert parser is not None

    html = """
    <section>
      <a href="https://responsiblegambling.org/about-rgc/rgc-news/">
        RGC News Home
      </a>
      <a href="https://responsiblegambling.org/about-rgc/rgc-news/rgc-and-icrg-partner-to-drive-global-gambling-harm-prevention/">
        Learn more
      </a>
    </section>
    """

    result = parser.parse_listing(
        listing_html=html,
        source_url="https://responsiblegambling.org/about-rgc/rgc-news/",
        company_name="Responsible Gambling Council",
    )

    assert result.candidate_urls == [
        "https://responsiblegambling.org/about-rgc/rgc-news/rgc-and-icrg-partner-to-drive-global-gambling-harm-prevention/"
    ]
