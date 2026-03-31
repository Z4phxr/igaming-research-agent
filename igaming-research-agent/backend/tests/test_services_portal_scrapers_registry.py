from app.services.portal_scrapers.parsers.ags_html import AgsHtmlParser
from app.services.portal_scrapers.parsers.aga_html import AgaHtmlParser
from app.services.portal_scrapers.parsers.aristocrat_html import AristocratHtmlParser
from app.services.portal_scrapers.parsers.bally_html import BallyHtmlParser
from app.services.portal_scrapers.parsers.bettercollective_html import BetterCollectiveHtmlParser
from app.services.portal_scrapers.parsers.bet365_html import Bet365HtmlParser
from app.services.portal_scrapers.parsers.betmgm_html import BetMgmHtmlParser
from app.services.portal_scrapers.parsers.bragg_html import BraggHtmlParser
from app.services.portal_scrapers.parsers.caesars_html import CaesarsHtmlParser
from app.services.portal_scrapers.parsers.catenamedia_html import CatenaMediaHtmlParser
from app.services.portal_scrapers.parsers.config_driven_html import ConfigDrivenHtmlParser
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
from app.services.portal_scrapers.registry import resolve_listing_parser
from app.services.portal_scrapers.parsers.kambi_html import KambiHtmlParser
from app.services.portal_scrapers.parsers.kalshi_html import KalshiHtmlParser
from app.services.portal_scrapers.parsers.lnw_html import LnwHtmlParser
from app.services.portal_scrapers.parsers.michigan_mgcb_html import MichiganMgcbHtmlParser
from app.services.portal_scrapers.parsers.penn_html import PennHtmlParser
from app.services.portal_scrapers.parsers.playtech_html import PlaytechHtmlParser
from app.services.portal_scrapers.parsers.polymarket_prnewswire_html import PolymarketPrnewswireHtmlParser
from app.services.portal_scrapers.parsers.pragmaticplay_html import PragmaticPlayHtmlParser
from app.services.portal_scrapers.parsers.prizepicks_html import PrizePicksHtmlParser
from app.services.portal_scrapers.parsers.rsi_html import RsiHtmlParser
from app.services.portal_scrapers.parsers.scientificgames_html import ScientificGamesHtmlParser
from app.services.portal_scrapers.parsers.sportradar_html import SportradarHtmlParser
from app.services.portal_scrapers.parsers.underdog_html import UnderdogHtmlParser
from app.services.portal_scrapers.parsers.wynn_html import WynnHtmlParser


def test_registry_resolves_kalshi_parser_for_kalshi_source():
    parser = resolve_listing_parser("https://news.kalshi.com/t/announcements", "Kalshi")
    assert isinstance(parser, KalshiHtmlParser)


def test_registry_returns_none_for_unknown_source():
    parser = resolve_listing_parser("https://example.com/news", "Example Corp")
    assert parser is None


def test_registry_resolves_evolution_parser_for_evolution_source():
    parser = resolve_listing_parser("https://www.evolution.com/news", "Evolution Gaming")
    assert isinstance(parser, EvolutionHtmlParser)


def test_registry_resolves_aristocrat_parser_for_aristocrat_source():
    parser = resolve_listing_parser("https://www.aristocrat.com/news/", "Aristocrat Leisure")
    assert isinstance(parser, AristocratHtmlParser)


def test_registry_resolves_ags_parser_for_ags_source():
    parser = resolve_listing_parser("https://newsroom.playags.com", "AGS (PlayAGS)")
    assert isinstance(parser, AgsHtmlParser)


def test_registry_resolves_aga_parser_for_aga_source():
    parser = resolve_listing_parser("https://www.americangaming.org/newsroom/", "American Gaming Association")
    assert isinstance(parser, AgaHtmlParser)


def test_registry_resolves_gdcgroup_parser_for_gdcgroup_source():
    parser = resolve_listing_parser("https://www.gdcgroup.com/media-center", "Gambling.com Group")
    assert isinstance(parser, GdcGroupHtmlParser)


def test_registry_resolves_bettercollective_parser_for_bettercollective_source():
    parser = resolve_listing_parser("https://bettercollective.com/press-releases/", "Better Collective")
    assert isinstance(parser, BetterCollectiveHtmlParser)


def test_registry_resolves_catenamedia_parser_for_catenamedia_source():
    parser = resolve_listing_parser("https://www.catenamedia.com/investors/press-releases", "Catena Media")
    assert isinstance(parser, CatenaMediaHtmlParser)


def test_registry_resolves_betmgm_parser_for_betmgm_source():
    parser = resolve_listing_parser("https://sports.betmgm.com/en/blog", "BetMGM")
    assert isinstance(parser, BetMgmHtmlParser)


def test_registry_resolves_bragg_parser_for_bragg_source():
    parser = resolve_listing_parser("https://bragg.group/news/", "Bragg")
    assert isinstance(parser, BraggHtmlParser)


def test_registry_resolves_bet365_parser_for_bet365_source():
    parser = resolve_listing_parser(
        "https://news.bet365.com/en-us/sport/more-sports-and-news/2022102012405478121",
        "Bet365",
    )
    assert isinstance(parser, Bet365HtmlParser)


def test_registry_resolves_bally_parser_for_bally_source():
    parser = resolve_listing_parser("https://www.ballys.com/news/default.aspx", "Bally's Interactive")
    assert isinstance(parser, BallyHtmlParser)


def test_registry_resolves_caesars_parser_for_caesars_source():
    parser = resolve_listing_parser("https://investor.caesars.com/press-releases", "Caesars Sportsbook")
    assert isinstance(parser, CaesarsHtmlParser)


def test_registry_resolves_fanduel_parser_for_fanduel_source():
    parser = resolve_listing_parser("https://www.fanduel.com/about/news", "FanDuel")
    assert isinstance(parser, FanDuelHtmlParser)


def test_registry_resolves_fanatics_parser_for_fanatics_source():
    parser = resolve_listing_parser("https://www.fanaticsinc.com/press-releases", "Fanatics Sportsbook")
    assert isinstance(parser, FanaticsHtmlParser)


def test_registry_resolves_draftkings_parser_for_draftkings_source():
    parser = resolve_listing_parser("https://www.draftkings.com/news-about", "DraftKings")
    assert isinstance(parser, DraftKingsHtmlParser)


def test_registry_resolves_hardrock_parser_for_hardrock_source():
    parser = resolve_listing_parser("https://www.hardrock.com/blog", "Hard Rock Bet")
    assert isinstance(parser, HardRockHtmlParser)


def test_registry_resolves_geniussports_parser_for_geniussports_source():
    parser = resolve_listing_parser("https://www.geniussports.com/newsroom/", "Genius Sports")
    assert isinstance(parser, GeniusSportsHtmlParser)


def test_registry_resolves_geocomply_parser_for_geocomply_source():
    parser = resolve_listing_parser("https://www.geocomply.com/awards-and-press/", "GeoComply")
    assert isinstance(parser, GeocomplyHtmlParser)


def test_registry_resolves_ic360_parser_for_ic360_source():
    parser = resolve_listing_parser("https://ic360.io/media", "IC360")
    assert isinstance(parser, Ic360HtmlParser)


def test_registry_resolves_igt_parser_for_igt_source():
    parser = resolve_listing_parser("https://www.igt.com/explore-igt/news/news", "IGT (+ Everi)")
    assert isinstance(parser, IgtHtmlParser)


def test_registry_resolves_lnw_parser_for_lnw_source():
    parser = resolve_listing_parser("https://explore.lnw.com/newsroom/", "Light & Wonder")
    assert isinstance(parser, LnwHtmlParser)


def test_registry_resolves_kambi_parser_for_kambi_source():
    parser = resolve_listing_parser("https://www.kambi.com/news-insights/", "Kambi")
    assert isinstance(parser, KambiHtmlParser)


def test_registry_resolves_polymarket_prnewswire_parser_for_polymarket_source():
    parser = resolve_listing_parser("https://www.prnewswire.com/news/polymarket/", "Polymarket")
    assert isinstance(parser, PolymarketPrnewswireHtmlParser)


def test_registry_resolves_penn_parser_for_penn_source():
    parser = resolve_listing_parser(
        "https://investors.pennentertainment.com/press-releases",
        "ESPN Bet / PENN Entertainment",
    )
    assert isinstance(parser, PennHtmlParser)


def test_registry_resolves_playtech_parser_for_playtech_source():
    parser = resolve_listing_parser("https://www.playtech.com/category/press-releases/#grid", "Playtech")
    assert isinstance(parser, PlaytechHtmlParser)


def test_registry_resolves_pragmaticplay_parser_for_pragmaticplay_source():
    parser = resolve_listing_parser("https://www.pragmaticplay.com/en/news/#", "Pragmatic Play")
    assert isinstance(parser, PragmaticPlayHtmlParser)


def test_registry_resolves_prizepicks_parser_for_prizepicks_source():
    parser = resolve_listing_parser("https://www.prizepicks.com/newsroom", "PrizePicks")
    assert isinstance(parser, PrizePicksHtmlParser)


def test_registry_resolves_rsi_parser_for_rsi_source():
    parser = resolve_listing_parser(
        "https://ir.rushstreetinteractive.com/news/default.aspx",
        "BetRivers / Rush Street Interactive",
    )
    assert isinstance(parser, RsiHtmlParser)


def test_registry_resolves_scientificgames_parser_for_scientificgames_source():
    parser = resolve_listing_parser("https://www.scientificgames.com/news/", "Scientific Games")
    assert isinstance(parser, ScientificGamesHtmlParser)


def test_registry_resolves_sportradar_parser_for_sportradar_source():
    parser = resolve_listing_parser("https://sportradar.com/content-hub/", "Sportradar")
    assert isinstance(parser, SportradarHtmlParser)


def test_registry_resolves_underdog_parser_for_underdog_source():
    parser = resolve_listing_parser("https://www.underdogfantasy.com/news", "Underdog Fantasy")
    assert isinstance(parser, UnderdogHtmlParser)


def test_registry_resolves_wynn_parser_for_wynn_source():
    parser = resolve_listing_parser("https://investors.wynnresorts.com/press-releases", "WynnBET")
    assert isinstance(parser, WynnHtmlParser)


def test_registry_resolves_config_driven_parser_for_configured_source():
    parser = resolve_listing_parser("https://config-driven.example/news", "Demo Corp")
    assert isinstance(parser, ConfigDrivenHtmlParser)


def test_registry_resolves_config_driven_parser_for_nj_dge_source():
    parser = resolve_listing_parser(
        "https://www.njoag.gov/about/divisions-and-offices/division-of-gaming-enforcement-home/news-and-updates/",
        "New Jersey DGE",
    )
    assert isinstance(parser, ConfigDrivenHtmlParser)


def test_registry_resolves_config_driven_parser_for_pa_source():
    parser = resolve_listing_parser(
        "https://gamingcontrolboard.pa.gov/news-and-transparency/press-release",
        "Pennsylvania Gaming Control Board",
    )
    assert isinstance(parser, ConfigDrivenHtmlParser)


def test_registry_resolves_config_driven_parser_for_mgcb_source():
    parser = resolve_listing_parser("https://www.michigan.gov/mgcb/news", "Michigan Gaming Control Board")
    assert isinstance(parser, MichiganMgcbHtmlParser)


def test_registry_resolves_config_driven_parser_for_nv_source():
    parser = resolve_listing_parser(
        "https://www.gaming.nv.gov/about-us/press-releases-public-statements/",
        "Nevada Gaming Control Board",
    )
    assert isinstance(parser, ConfigDrivenHtmlParser)


def test_registry_resolves_config_driven_parser_for_ny_source():
    parser = resolve_listing_parser("https://gaming.ny.gov/newsroom", "New York Gaming Commission")
    assert isinstance(parser, ConfigDrivenHtmlParser)


def test_registry_resolves_config_driven_parser_for_igb_source():
    parser = resolve_listing_parser("https://igb.illinois.gov/news/press-releases.html", "Illinois Gaming Board")
    assert isinstance(parser, IllinoisIgbHtmlParser)


def test_registry_resolves_config_driven_parser_for_ohio_source():
    parser = resolve_listing_parser(
        "https://casinocontrol.ohio.gov/home/news-and-events/all-news/",
        "Ohio Casino Control Commission",
    )
    assert isinstance(parser, ConfigDrivenHtmlParser)


def test_registry_resolves_config_driven_parser_for_colorado_source():
    parser = resolve_listing_parser("https://sbg.colorado.gov/press-releases", "Colorado Division of Gaming")
    assert isinstance(parser, ConfigDrivenHtmlParser)


def test_registry_resolves_config_driven_parser_for_wv_source():
    parser = resolve_listing_parser(
        "https://wvlottery.com/news-and-winning/news-and-offers/news-and-events",
        "West Virginia Lottery",
    )
    assert isinstance(parser, ConfigDrivenHtmlParser)


def test_registry_resolves_config_driven_parser_for_ct_source():
    parser = resolve_listing_parser(
        "https://portal.ct.gov/dcp/gaming-division/gaming/gaming-division-news?language=en_US",
        "Connecticut Gaming Division",
    )
    assert isinstance(parser, ConfigDrivenHtmlParser)


def test_registry_resolves_config_driven_parser_for_nigc_source():
    parser = resolve_listing_parser("https://www.nigc.gov/downloads/news/", "National Indian Gaming Commission")
    assert isinstance(parser, ConfigDrivenHtmlParser)


def test_registry_resolves_config_driven_parser_for_sba_source():
    parser = resolve_listing_parser("https://sportsbettingalliance.org/about/", "Sports Betting Alliance")
    assert isinstance(parser, ConfigDrivenHtmlParser)


def test_registry_resolves_config_driven_parser_for_rgc_source_by_company_name():
    parser = resolve_listing_parser("https://www.responsiblegambling.org/news", "Responsible Gambling Council")
    assert isinstance(parser, ConfigDrivenHtmlParser)
