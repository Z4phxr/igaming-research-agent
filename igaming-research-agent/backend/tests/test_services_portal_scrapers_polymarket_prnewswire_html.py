from app.services.portal_scrapers.parsers.polymarket_prnewswire_html import PolymarketPrnewswireHtmlParser


def test_polymarket_prnewswire_parser_returns_tracking_redirect_reason():
    parser = PolymarketPrnewswireHtmlParser()
    html = "https://12056271.fls.doubleclick.net/activityi;src=12056271;~oref=https://www.prnewswire.com/news/polymarket/"

    result = parser.parse_listing(html, "https://www.prnewswire.com/news/polymarket/", "Polymarket")

    assert result.candidate_urls == []
    assert result.empty_reason == "tracking_redirect_blocked"
