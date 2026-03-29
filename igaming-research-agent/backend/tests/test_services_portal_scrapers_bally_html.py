from app.services.portal_scrapers.parsers.bally_html import BallyHtmlParser


def test_bally_parser_returns_q4_auth_reason():
    parser = BallyHtmlParser()
    listing_html = "https://auth.platform.q4inc.com/auth/publicAuthRedirect?error=login_required"

    result = parser.parse_listing(listing_html, "https://www.ballys.com/news/default.aspx", "Bally's Interactive")

    assert result.candidate_urls == []
    assert result.empty_reason == "q4_auth_required"
