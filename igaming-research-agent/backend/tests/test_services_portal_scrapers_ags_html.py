from app.services.portal_scrapers.parsers.ags_html import AgsHtmlParser


def test_ags_parser_extracts_release_like_links():
    parser = AgsHtmlParser()
    listing_html = """
    <a href='/news/ags-announces-new-product-line'>AGS Announces New Product Line</a>
    <a href='/press-releases/ags-reports-quarterly-results'>AGS Reports Quarterly Results</a>
    <a href='/about'>About</a>
    """

    result = parser.parse_listing(
        listing_html=listing_html,
        source_url='https://newsroom.playags.com',
        company_name='AGS (PlayAGS)',
    )

    assert result.empty_reason is None
    assert result.candidate_urls == [
        'https://newsroom.playags.com/news/ags-announces-new-product-line',
        'https://newsroom.playags.com/press-releases/ags-reports-quarterly-results',
    ]


def test_ags_parser_returns_tls_reason_on_certificate_error_page():
    parser = AgsHtmlParser()
    listing_html = 'SSL CERTIFICATE VERIFY FAILED - certificate error'

    result = parser.parse_listing(
        listing_html=listing_html,
        source_url='https://newsroom.playags.com',
        company_name='AGS (PlayAGS)',
    )

    assert result.candidate_urls == []
    assert result.empty_reason == 'tls_certificate_error'
