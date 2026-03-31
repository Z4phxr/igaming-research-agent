import datetime

from app.services.portal_scrapers.parsers.bet365_html import Bet365HtmlParser


def test_bet365_parser_extracts_article_links_and_date_from_url():
    parser = Bet365HtmlParser()
    listing_html = """
    <a href='/en-us/article/bet365-announces-official-launch-in-maryland/2025090211305963186'>bet365 announces official launch in Maryland</a>
    <a href='/en-us/article/bet365-announces-official-launch-in-kansas/2025080609354100678'>bet365 announces official launch in Kansas</a>
    """

    result = parser.parse_listing(
        listing_html=listing_html,
        source_url='https://news.bet365.com/en-us/sport/more-sports-and-news/2022102012405478121',
        company_name='Bet365',
    )

    assert result.empty_reason is None
    assert len(result.candidate_urls) == 2
    assert result.candidate_published_dates[result.candidate_urls[0]] == datetime.datetime(2025, 9, 2)


def test_bet365_parser_handles_featured_and_story_grid_structure():
        parser = Bet365HtmlParser()
        listing_html = """
        <div id="maincontent"></div>
        <div class="fsh-Wrapper">
            <a class="fsh-ParagraphWrapper" href="/en-us/article/bet365-announces-official-launch-in-maryland/2025090211305963186">
                <h2 class="fsh-TextHeader">bet365 announces official launch in Maryland</h2>
            </a>
        </div>
        <section class="sg-Container_Outer">
            <ul class="sg-Container_Inner">
                <li class="sg-StoryContainer">
                    <a class="sg-TextContainer_Header" href="/en-us/article/bet365-announces-official-launch-in-kansas/2025080609354100678">
                        <h3 class="sg-Header">bet365 announces official launch in Kansas</h3>
                    </a>
                </li>
            </ul>
        </section>
        """

        result = parser.parse_listing(
                listing_html=listing_html,
                source_url="https://news.bet365.com/en-us/sport/more-sports-and-news/2022102012405478121",
                company_name="Bet365",
        )

        assert result.empty_reason is None
        assert result.candidate_urls == [
                "https://news.bet365.com/en-us/article/bet365-announces-official-launch-in-maryland/2025090211305963186",
                "https://news.bet365.com/en-us/article/bet365-announces-official-launch-in-kansas/2025080609354100678",
        ]
