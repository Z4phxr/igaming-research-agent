import datetime

from app.services.portal_scrapers.parsers.gdcgroup_html import GdcGroupHtmlParser


def test_gdcgroup_parser_extracts_media_center_links_and_dates():
    parser = GdcGroupHtmlParser()
    listing_html = """
    <a href='https://www.gdcgroup.com/media-center/gambling-com-group-ready-for-launch-of-online-sports-betting-in-missouri'>Gambling.com Group Ready for Launch of Online Sports Betting in Missouri</a>
    <span>December 1st, 2025</span>
    <a href='https://www.gdcgroup.com/media-center/gambling-com-group-announces-2025-american-gambling-awards-winners'>Gambling.com Group Announces 2025 American Gambling Awards Winners</a>
    <span>November 19th, 2025</span>
    """

    result = parser.parse_listing(listing_html, "https://www.gdcgroup.com/media-center", "Gambling.com Group")

    assert result.empty_reason is None
    assert len(result.candidate_urls) == 2
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2025, 12, 1)


def test_gdcgroup_parser_extracts_embedded_articles_payload():
        parser = GdcGroupHtmlParser()
        listing_html = """
        <news-articles-component
            :articles="[{&quot;page_title&quot;:&quot;Gambling.com Group Ready for Launch of Online Sports Betting in Missouri&quot;,&quot;publish_date&quot;:&quot;December 1st, 2025&quot;,&quot;article_url&quot;:&quot;/media-center/gambling-com-group-ready-for-launch-of-online-sports-betting-in-missouri&quot;},{&quot;page_title&quot;:&quot;Gambling.com Group Announces 2025 American Gambling Awards Winners&quot;,&quot;publish_date&quot;:&quot;November 19th, 2025&quot;,&quot;article_url&quot;:&quot;/media-center/gambling-com-group-announces-2025-american-gambling-awards-winners&quot;}]">
        </news-articles-component>
        """

        result = parser.parse_listing(listing_html, "https://www.gdcgroup.com/media-center", "Gambling.com Group")

        assert result.empty_reason is None
        assert len(result.candidate_urls) == 2
        assert result.candidate_urls[0].endswith("/media-center/gambling-com-group-ready-for-launch-of-online-sports-betting-in-missouri")
        assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2025, 12, 1)


def test_gdcgroup_parser_does_not_flag_cloudflare_token_when_payload_exists():
        parser = GdcGroupHtmlParser()
        listing_html = """
        <div class="__cf_email__">protected</div>
        <news-articles-component
            :articles="[{&quot;page_title&quot;:&quot;Gambling.com Group Ready for Launch of Online Sports Betting in Missouri&quot;,&quot;publish_date&quot;:&quot;December 1st, 2025&quot;,&quot;article_url&quot;:&quot;/media-center/gambling-com-group-ready-for-launch-of-online-sports-betting-in-missouri&quot;}]">
        </news-articles-component>
        """

        result = parser.parse_listing(listing_html, "https://www.gdcgroup.com/media-center", "Gambling.com Group")

        assert result.empty_reason is None
        assert result.candidate_urls


def test_gdcgroup_parser_flags_real_bot_block_when_no_links():
        parser = GdcGroupHtmlParser()
        listing_html = """
        <html>
            <head><title>Attention Required! | Cloudflare</title></head>
            <body>Please enable cookies and captcha to continue.</body>
        </html>
        """

        result = parser.parse_listing(listing_html, "https://www.gdcgroup.com/media-center", "Gambling.com Group")

        assert result.candidate_urls == []
        assert result.empty_reason == "bot_protection_blocked"
