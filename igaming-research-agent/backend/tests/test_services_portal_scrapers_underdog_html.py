import datetime

from app.services.portal_scrapers.parsers.underdog_html import UnderdogHtmlParser


def test_underdog_parser_keeps_press_release_rows_only():
    parser = UnderdogHtmlParser()
    listing_html = """
    <a href='/news/fantasy-sports-firm-underdog-acquires-derivatives-exchange'>March 9, 2026 News Fantasy Sports Firm Underdog Acquires Derivatives Exchange</a>
    <a href='/news/underdog-acquires-cftc-registered-designated-contract-market-dcm-and-derivatives-clearing-organization-dco'>March 9, 2026 Press Releases Underdog Acquires CFTC-Registered Designated Contract Market (DCM) and Derivatives Clearing Organization (DCO)</a>
    <a href='/news/underdogs-pioneering-responsible-play-fund-guarddog-announces-new-investment-in-regen'>January 21, 2026 2 min Press Releases Underdog’s Pioneering Responsible Play Fund, GuardDog, Announces New Investment in Regen</a>
    """

    result = parser.parse_listing(listing_html, "https://www.underdogfantasy.com/news", "Underdog Fantasy")

    assert result.empty_reason is None
    assert len(result.candidate_urls) == 2
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2026, 3, 9)
