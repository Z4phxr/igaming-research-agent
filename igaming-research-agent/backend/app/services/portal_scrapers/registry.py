from __future__ import annotations

from app.services.portal_scrapers.parsers.ags_html import AgsHtmlParser
from app.services.portal_scrapers.parsers.aga_html import AgaHtmlParser
from app.services.portal_scrapers.parsers.aristocrat_html import AristocratHtmlParser
from app.services.portal_scrapers.base import PortalListingParser
from app.services.portal_scrapers.parsers.bettercollective_html import BetterCollectiveHtmlParser
from app.services.portal_scrapers.parsers.bragg_html import BraggHtmlParser
from app.services.portal_scrapers.parsers.betmgm_html import BetMgmHtmlParser
from app.services.portal_scrapers.parsers.bet365_html import Bet365HtmlParser
from app.services.portal_scrapers.parsers.caesars_html import CaesarsHtmlParser
from app.services.portal_scrapers.parsers.catenamedia_html import CatenaMediaHtmlParser
from app.services.portal_scrapers.parsers.config_driven_html import ConfigDrivenHtmlParser, HtmlListingParserConfig
from app.services.portal_scrapers.parsers.draftkings_html import DraftKingsHtmlParser
from app.services.portal_scrapers.parsers.evolution_html import EvolutionHtmlParser
from app.services.portal_scrapers.parsers.fanduel_html import FanDuelHtmlParser
from app.services.portal_scrapers.parsers.fanatics_html import FanaticsHtmlParser
from app.services.portal_scrapers.parsers.gdcgroup_html import GdcGroupHtmlParser
from app.services.portal_scrapers.parsers.geocomply_html import GeocomplyHtmlParser
from app.services.portal_scrapers.parsers.geniussports_html import GeniusSportsHtmlParser
from app.services.portal_scrapers.parsers.hardrock_html import HardRockHtmlParser
from app.services.portal_scrapers.parsers.ic360_html import Ic360HtmlParser
from app.services.portal_scrapers.parsers.igt_html import IgtHtmlParser
from app.services.portal_scrapers.parsers.illinois_igb_html import IllinoisIgbHtmlParser
from app.services.portal_scrapers.parsers.kambi_html import KambiHtmlParser
from app.services.portal_scrapers.parsers.kalshi_html import KalshiHtmlParser
from app.services.portal_scrapers.parsers.michigan_mgcb_html import MichiganMgcbHtmlParser
from app.services.portal_scrapers.parsers.penn_html import PennHtmlParser
from app.services.portal_scrapers.parsers.playtech_html import PlaytechHtmlParser
from app.services.portal_scrapers.parsers.polymarket_prnewswire_html import PolymarketPrnewswireHtmlParser
from app.services.portal_scrapers.parsers.pragmaticplay_html import PragmaticPlayHtmlParser
from app.services.portal_scrapers.parsers.prizepicks_html import PrizePicksHtmlParser
from app.services.portal_scrapers.parsers.rsi_html import RsiHtmlParser
from app.services.portal_scrapers.parsers.rgc_html import RgcHtmlParser
from app.services.portal_scrapers.parsers.bally_html import BallyHtmlParser
from app.services.portal_scrapers.parsers.lnw_html import LnwHtmlParser
from app.services.portal_scrapers.parsers.scientificgames_html import ScientificGamesHtmlParser
from app.services.portal_scrapers.parsers.sportradar_html import SportradarHtmlParser
from app.services.portal_scrapers.parsers.underdog_html import UnderdogHtmlParser
from app.services.portal_scrapers.parsers.wynn_html import WynnHtmlParser


_PARSERS: list[PortalListingParser] = [
    AgsHtmlParser(),
    AgaHtmlParser(),
    AristocratHtmlParser(),
    BetterCollectiveHtmlParser(),
    Bet365HtmlParser(),
    BetMgmHtmlParser(),
    CaesarsHtmlParser(),
    CatenaMediaHtmlParser(),
    DraftKingsHtmlParser(),
    EvolutionHtmlParser(),
    FanDuelHtmlParser(),
    FanaticsHtmlParser(),
    GdcGroupHtmlParser(),
    HardRockHtmlParser(),
    GeniusSportsHtmlParser(),
    IgtHtmlParser(),
    IllinoisIgbHtmlParser(),
    KalshiHtmlParser(),
    PennHtmlParser(),
    RgcHtmlParser(),
    RsiHtmlParser(),
    BallyHtmlParser(),
    BraggHtmlParser(),
    LnwHtmlParser(),
    KambiHtmlParser(),
    MichiganMgcbHtmlParser(),
    Ic360HtmlParser(),
    GeocomplyHtmlParser(),
    PlaytechHtmlParser(),
    PolymarketPrnewswireHtmlParser(),
    PragmaticPlayHtmlParser(),
    PrizePicksHtmlParser(),
    ScientificGamesHtmlParser(),
    SportradarHtmlParser(),
    UnderdogHtmlParser(),
    WynnHtmlParser(),
]

_CONFIG_DRIVEN_CONFIGS: list[HtmlListingParserConfig] = [
    HtmlListingParserConfig(
        name="new-jersey-dge",
        source_url_contains=("njoag.gov/about/divisions-and-offices/division-of-gaming-enforcement-home/news-and-updates",),
        company_name_contains=("new jersey dge", "division of gaming enforcement"),
        scope_selector="tbody",
        item_selector="tr td a[href$='.pdf']",
        link_href_must_contain=("/oag/ge/docs/financials/pressrelease", ".pdf"),
        link_href_excludes=("#",),
        blocked_markers=("access denied", "captcha", "cloudflare", "track/cei"),
        empty_reason_no_items="no_dge_news_links",
    ),
    HtmlListingParserConfig(
        name="pennsylvania-gaming-control-board",
        source_url_contains=("gamingcontrolboard.pa.gov/news-and-transparency/press-release",),
        company_name_contains=("pennsylvania gaming control board",),
        item_selector="div.press-release-block, a[href*='/news-and-transparency/press-release/']",
        link_selector="div.press-release-readmore a[href]",
        title_selector="div.press-release-title",
        date_selector="div.press-release-date",
        date_formats=("%m-%d-%Y",),
        link_href_excludes=("?page=", "#"),
        empty_reason_no_items="no_pa_press_release_links",
    ),
    HtmlListingParserConfig(
        name="nevada-gaming-control-board",
        source_url_contains=("gaming.nv.gov/about-us/press-releases-public-statements",),
        company_name_contains=("nevada gaming control board",),
        item_selector="a[href*='.pdf']",
        link_href_must_contain=(".pdf",),
        empty_reason_no_items="no_nv_press_release_documents",
    ),
    HtmlListingParserConfig(
        name="new-york-gaming-commission",
        source_url_contains=("gaming.ny.gov/newsroom",),
        company_name_contains=("new york gaming commission",),
        item_selector="a[href*='/news/']",
        link_href_must_contain=("/news/",),
        link_href_excludes=("/newsroom", "?page=", "#"),
        empty_reason_no_items="no_ny_newsroom_links",
    ),
    HtmlListingParserConfig(
        name="ohio-casino-control-commission",
        source_url_contains=("casinocontrol.ohio.gov/home/news-and-events/all-news",),
        company_name_contains=("ohio casino control commission",),
        item_selector="a[href*='casino.ohio.gov'], a[href*='casinocontrol.ohio.gov']",
        blocked_markers=("404", "not found", "access denied", "enable javascript"),
        empty_reason_no_items="no_ohio_news_links",
    ),
    HtmlListingParserConfig(
        name="colorado-division-of-gaming",
        source_url_contains=("sbg.colorado.gov/press-releases",),
        company_name_contains=("colorado division of gaming",),
        item_selector="a[href*='sbg.colorado.gov/news-article/'], a[href*='sbg.colorado.gov/Problem_Gambling_Awareness']",
        link_href_must_contain=("sbg.colorado.gov",),
        empty_reason_no_items="no_colorado_press_release_links",
    ),
    HtmlListingParserConfig(
        name="west-virginia-lottery",
        source_url_contains=("wvlottery.com/news-and-winning/news-and-offers/news-and-events",),
        company_name_contains=("west virginia lottery",),
        item_selector="a[href*='/news-and-winning/']",
        blocked_markers=("403", "forbidden", "access denied", "cloudflare"),
        empty_reason_no_items="no_wv_lottery_news_links",
    ),
    HtmlListingParserConfig(
        name="connecticut-gaming-division",
        source_url_contains=("portal.ct.gov/dcp/gaming-division/gaming/gaming-division-news",),
        company_name_contains=("connecticut gaming division",),
        item_selector="a[href*='ct.gov/dosr'], a[href*='dosr/lib/dosr']",
        empty_reason_no_items="no_ct_gaming_news_links",
    ),
    HtmlListingParserConfig(
        name="national-indian-gaming-commission",
        source_url_contains=("nigc.gov/downloads/news",),
        company_name_contains=("national indian gaming commission",),
        item_selector="h2 a[href*='/download/']",
        link_href_must_contain=("/download/",),
        empty_reason_no_items="no_nigc_news_links",
    ),
    HtmlListingParserConfig(
        name="sports-betting-alliance",
        source_url_contains=("sportsbettingalliance.org/about",),
        company_name_contains=("sports betting alliance",),
        scope_selector="div.post_types.post_types_0",
        item_selector="div.lwp_post_carousel_item",
        link_selector="a.lwp_post_title[href]",
        date_selector="span.lwp_meta_date",
        date_formats=("%b %d, %Y",),
        link_href_must_contain=("sportsbettingalliance.org",),
        link_href_excludes=(
            "/about/",
            "/take-action",
            "/sports-betting/",
            "/i-gaming/",
            "/responsible-gaming/",
            "/privacy-policy",
            "mailto:",
            "#",
        ),
        empty_reason_no_items="no_sba_latest_links",
    ),
    HtmlListingParserConfig(
        name="responsible-gambling-council",
        source_url_contains=("responsiblegambling.org/news", "responsiblegambling.org/about-rgc/rgc-news"),
        company_name_contains=("responsible gambling council",),
        item_selector="a[href*='/about-rgc/rgc-news/']",
        link_href_must_contain=("/about-rgc/rgc-news/",),
        empty_reason_no_items="no_rgc_news_links",
    ),
    # Template-like starter config to speed up onboarding of simple HTML listing portals.
    HtmlListingParserConfig(
        name="demo-config-driven-portal",
        source_url_contains=("config-driven.example",),
        item_selector="article.release-item",
        link_selector="a[href]",
        title_selector="h2, h3",
        date_selector="time",
        date_formats=("%Y-%m-%d",),
        descending_chronological=True,
        empty_reason_no_items="no_config_release_items",
    )
]

_CONFIG_DRIVEN_PARSER = ConfigDrivenHtmlParser(_CONFIG_DRIVEN_CONFIGS)


def resolve_listing_parser(source_url: str, company_name: str) -> PortalListingParser | None:
    for parser in _PARSERS:
        if parser.matches(source_url=source_url, company_name=company_name):
            return parser
    if _CONFIG_DRIVEN_PARSER.matches(source_url=source_url, company_name=company_name):
        return _CONFIG_DRIVEN_PARSER
    return None


def list_registered_parsers() -> list[PortalListingParser]:
    return list(_PARSERS) + [_CONFIG_DRIVEN_PARSER]
