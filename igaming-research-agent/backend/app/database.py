"""Database setup for SQLAlchemy connection/session management.

TODO: Replace metadata create_all with migration-based schema management.
"""

import os
from urllib.parse import urlparse

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

RELEASE_SOURCE_MIGRATION_NAME = "2026_03_29_release_sources_full_refresh"

DEFAULT_RELEASE_SOURCES: list[dict[str, str]] = [
    {
        "company_name": "FanDuel",
        "category": "Operator",
        "source_url": "https://www.fanduel.com/about/news",
        "notes": "Zaklady sportowe + kasyno online, #1 US market share",
    },
    {
        "company_name": "DraftKings",
        "category": "Operator",
        "source_url": "https://www.draftkings.com/news-about",
        "notes": "Zaklady + kasyno + DFS, notowany na NASDAQ (DKNG)",
    },
    {
        "company_name": "BetMGM",
        "category": "Operator",
        "source_url": "https://sports.betmgm.com/en/blog/press/",
        "notes": "JV: MGM Resorts + Entain",
    },
    {
        "company_name": "Caesars Sportsbook",
        "category": "Operator",
        "source_url": "https://investor.caesars.com/press-releases",
        "notes": "Operator + kasyno, Caesars Entertainment",
    },
    {
        "company_name": "ESPN Bet / PENN Entertainment",
        "category": "Operator",
        "source_url": "https://investors.pennentertainment.com/press-releases",
        "notes": "PENN + ESPN, rebranding z Barstool",
    },
    {
        "company_name": "BetRivers / Rush Street Interactive",
        "category": "Operator",
        "source_url": "https://ir.rushstreetinteractive.com/news/default.aspx",
        "notes": "RSI, kasyno online + sportsbook",
    },
    {
        "company_name": "Fanatics Sportsbook",
        "category": "Operator",
        "source_url": "https://www.fanaticsinc.com/press-releases",
        "notes": "Szybko rosnacy operator",
    },
    {
        "company_name": "Hard Rock Bet",
        "category": "Operator",
        "source_url": "https://www.hardrock.com/blog",
        "notes": "Operator kasyna + sportsbook",
    },
    {
        "company_name": "Bet365",
        "category": "Operator",
        "source_url": "https://news.bet365.com/en-us/sport/more-sports-and-news/2022102012405478121",
        "notes": "UK-operator, obecny w kilku stanach US",
    },
    {
        "company_name": "WynnBET",
        "category": "Operator",
        "source_url": "https://investors.wynnresorts.com/press-releases",
        "notes": "Wynn Resorts - sportsbook cyfrowy",
    },
    {
        "company_name": "Underdog Fantasy",
        "category": "Operator",
        "source_url": "https://www.underdogfantasy.com/news",
        "notes": "DFS + zaklady, dynamiczny wzrost",
    },
    {
        "company_name": "Bally's Interactive",
        "category": "Operator",
        "source_url": "https://www.ballys.com/news/default.aspx",
        "notes": "Online gaming + kasyna naziemne",
    },
    {
        "company_name": "Light & Wonder",
        "category": "Slot provider",
        "source_url": "https://explore.lnw.com/newsroom/",
        "notes": "Dostawca slotow, dawne Scientific Games Gaming",
    },
    {
        "company_name": "IGT (+ Everi)",
        "category": "Slot provider",
        "source_url": "https://www.igt.com/explore-igt/news/news",
        "notes": "Polaczenie IGT + Everi, Apollo, Las Vegas",
    },
    {
        "company_name": "Aristocrat Leisure",
        "category": "Slot provider",
        "source_url": "https://www.aristocrat.com/news/",
        "notes": "AU, duzy udzial US slots + iGaming",
    },
    {
        "company_name": "AGS (PlayAGS)",
        "category": "Slot provider",
        "source_url": "https://newsroom.playags.com",
        "notes": "Notowany NYSE, sloty + tabletop",
    },
    {
        "company_name": "Evolution Gaming",
        "category": "Tech/B2B",
        "source_url": "https://www.evolution.com/news/",
        "notes": "Live casino #1 na swiecie, B2B US operators",
    },
    {
        "company_name": "Playtech",
        "category": "Tech/B2B",
        "source_url": "https://www.playtech.com/category/press-releases/#grid",
        "notes": "B2B platforma, wejscie na rynek US",
    },
    {
        "company_name": "Pragmatic Play",
        "category": "Tech/B2B",
        "source_url": "https://www.pragmaticplay.com/en/news/#",
        "notes": "Sloty + live casino, US licensed operators",
    },
    {
        "company_name": "SBC Digital / Bragg Gaming",
        "category": "Tech/B2B",
        "source_url": "https://bragg.group/news/",
        "notes": "Content + PAM, notowany NASDAQ",
    },
    {
        "company_name": "Kambi Group",
        "category": "Tech/B2B",
        "source_url": "https://kambi.com/news-insights/",
        "notes": "B2B sportsbook engine (DraftKings uzywal)",
    },
    {
        "company_name": "IC360",
        "category": "Tech/B2B",
        "source_url": "https://ic360.io/media",
        "notes": "Regulatory tech dla iGaming US",
    },
    {
        "company_name": "GeoComply",
        "category": "Tech/B2B",
        "source_url": "https://www.geocomply.com/awards-and-press/",
        "notes": "Geolokalizacja, compliance dla US operators",
    },
    {
        "company_name": "Scientific Games (Lottery)",
        "category": "Tech/B2B",
        "source_url": "https://www.scientificgames.com/news/",
        "notes": "Loteria B2B, czesc po spin-offie L&W",
    },
    {
        "company_name": "Gambling.com Group",
        "category": "Affiliate",
        "source_url": "https://www.gdcgroup.com/media-center",
        "notes": "Affiliate + media, notowany NASDAQ",
    },
    {
        "company_name": "Better Collective",
        "category": "Affiliate",
        "source_url": "https://bettercollective.com/press-releases/",
        "notes": "Duzy gracz afiliacyjny US",
    },
    {
        "company_name": "Catena Media",
        "category": "Affiliate",
        "source_url": "https://www.catenamedia.com/investors/press-releases",
        "notes": "SEO + afiliacja, US rynek",
    },
    {
        "company_name": "Sportradar",
        "category": "Data/Integrity",
        "source_url": "https://sportradar.com/content-hub/",
        "notes": "Dane sportowe, oficjalny partner lig US",
    },
    {
        "company_name": "Genius Sports",
        "category": "Data/Integrity",
        "source_url": "https://www.geniussports.com/newsroom/",
        "notes": "NFL official data partner, notowany NYSE",
    },
    {
        "company_name": "American Gaming Association (AGA)",
        "category": "Media/Org",
        "source_url": "https://www.americangaming.org/newsroom/",
        "notes": "Branzowy trade body, regulatory",
    },
    {
        "company_name": "NJ Division of Gaming Enforcement",
        "category": "Regulator stanowy",
        "source_url": "https://www.njoag.gov/about/divisions-and-offices/division-of-gaming-enforcement-home/news-and-updates/",
        "notes": "NJ - najwazniejszy stan iGaming US",
    },
    {
        "company_name": "Pennsylvania Gaming Control Board",
        "category": "Regulator stanowy",
        "source_url": "https://gamingcontrolboard.pa.gov/news-and-transparency/press-release",
        "notes": "PA - drugi najwiekszy rynek",
    },
    {
        "company_name": "Michigan Gaming Control Board",
        "category": "Regulator stanowy",
        "source_url": "https://www.michigan.gov/mgcb/news",
        "notes": "MI - iGaming + sportsbook",
    },
    {
        "company_name": "Nevada Gaming Control Board",
        "category": "Regulator stanowy",
        "source_url": "https://www.gaming.nv.gov/about-us/press-releases-public-statements/",
        "notes": "NV - Vegas, poker online, NGCB",
    },
    {
        "company_name": "New York State Gaming Commission",
        "category": "Regulator stanowy",
        "source_url": "https://gaming.ny.gov/newsroom",
        "notes": "NY - najwiekszy rynek sportsbook US",
    },
    {
        "company_name": "Illinois Gaming Board",
        "category": "Regulator stanowy",
        "source_url": "https://igb.illinois.gov/news/press-releases.html",
        "notes": "IL - 2. rynek sportsbook, online casino pending",
    },
    {
        "company_name": "Ohio Casino Control Commission",
        "category": "Regulator stanowy",
        "source_url": "https://casinocontrol.ohio.gov/home/news-and-events/all-news/",
        "notes": "OH - sportsbook + kasyna",
    },
    {
        "company_name": "Colorado Division of Gaming",
        "category": "Regulator stanowy",
        "source_url": "https://sbg.colorado.gov/press-releases",
        "notes": "CO - mobile sportsbook, regulacje",
    },
    {
        "company_name": "West Virginia Lottery (iGaming)",
        "category": "Regulator stanowy",
        "source_url": "https://wvlottery.com/news-and-winning/news-and-offers/news-and-events",
        "notes": "WV - iGaming + sportsbook regulacje",
    },
    {
        "company_name": "Connecticut DOSR",
        "category": "Regulator stanowy",
        "source_url": "https://portal.ct.gov/dcp/gaming-division/gaming/gaming-division-news?language=en_US",
        "notes": "CT - sportsbook + iGaming",
    },
    {
        "company_name": "National Indian Gaming Commission",
        "category": "Regulator stanowy",
        "source_url": "https://www.nigc.gov/downloads/news/",
        "notes": "Federalny regulator tribal gaming US",
    },
    {
        "company_name": "Sports Betting Alliance (SBA)",
        "category": "Org. branzowa",
        "source_url": "https://sportsbettingalliance.org/about/",
        "notes": "FanDuel, DK, BetMGM, Fanatics, bet365",
    },
    {
        "company_name": "Responsible Gambling Council",
        "category": "Org. branzowa",
        "source_url": "https://responsiblegambling.org/about-rgc/rgc-news/",
        "notes": "Responsible gaming standards US/CA",
    },
    {
        "company_name": "PrizePicks",
        "category": "DFS",
        "source_url": "https://www.prizepicks.com/newsroom",
        "notes": "Pick'em DFS, obecny w wielu stanach",
    },
    {
        "company_name": "Kalshi",
        "category": "Org. branzowa",
        "source_url": "https://news.kalshi.com/t/announcements",
        "notes": "CFTC-regulated prediction markets US",
    },
    {
        "company_name": "Polymarket",
        "category": "Org. branzowa",
        "source_url": "https://www.prnewswire.com/news/polymarket/",
        "notes": "Blockchain prediction market, US-focused",
    },
]


def get_db():
    """FastAPI dependency for DB session.

    TODO: Add request-level tracing metadata to sessions if needed.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all registered tables.

    TODO: Switch to migration-based schema management.
    """
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    ensure_article_runtime_columns()
    ensure_report_runtime_columns()
    ensure_release_source_runtime_columns()
    ensure_app_migrations_table()
    apply_release_source_data_migration()
    ensure_prompt_templates_seeded()


def ensure_prompt_templates_seeded() -> None:
    """Create baseline prompt templates for prompt manager."""
    from app.services.prompt_manager import ensure_default_prompt_templates

    with SessionLocal() as session:
        ensure_default_prompt_templates(session)
        session.commit()


def ensure_article_runtime_columns() -> None:
    """Backfill newer Article columns in existing databases without migrations."""
    inspector = inspect(engine)
    if "articles" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("articles")}
    dialect = engine.dialect.name
    bool_default = "1" if dialect == "sqlite" else "TRUE"

    statements: list[str] = []
    if "raw_score" not in existing_columns:
        statements.append("ALTER TABLE articles ADD COLUMN raw_score INTEGER")
    if "passed_relevance_filter" not in existing_columns:
        statements.append(
            f"ALTER TABLE articles ADD COLUMN passed_relevance_filter BOOLEAN NOT NULL DEFAULT {bool_default}"
        )
    if "kept" not in existing_columns:
        statements.append(f"ALTER TABLE articles ADD COLUMN kept BOOLEAN NOT NULL DEFAULT {bool_default}")
    if "rejection_reason" not in existing_columns:
        statements.append("ALTER TABLE articles ADD COLUMN rejection_reason VARCHAR(64)")
    if "article_type" not in existing_columns:
        statements.append("ALTER TABLE articles ADD COLUMN article_type VARCHAR(32) NOT NULL DEFAULT 'top_story'")

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def ensure_report_runtime_columns() -> None:
    """Backfill newer Report columns in existing databases without migrations."""
    inspector = inspect(engine)
    if "reports" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("reports")}
    statements: list[str] = []
    if "briefing" not in existing_columns:
        statements.append("ALTER TABLE reports ADD COLUMN briefing TEXT")
    if "briefing_generated_at" not in existing_columns:
        statements.append("ALTER TABLE reports ADD COLUMN briefing_generated_at TIMESTAMP")
    if "articles_pipeline_ran_at" not in existing_columns:
        statements.append("ALTER TABLE reports ADD COLUMN articles_pipeline_ran_at TIMESTAMP")
    if "releases_pipeline_ran_at" not in existing_columns:
        statements.append("ALTER TABLE reports ADD COLUMN releases_pipeline_ran_at TIMESTAMP")

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def ensure_release_source_runtime_columns() -> None:
    """Backfill ReleaseSource columns for existing databases without migrations."""
    inspector = inspect(engine)
    if "release_sources" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("release_sources")}
    statements: list[str] = []
    if "created_at" not in existing_columns:
        statements.append("ALTER TABLE release_sources ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    if "updated_at" not in existing_columns:
        statements.append("ALTER TABLE release_sources ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    if "category" not in existing_columns:
        statements.append("ALTER TABLE release_sources ADD COLUMN category VARCHAR(64) NOT NULL DEFAULT ''")
    if "notes" not in existing_columns:
        statements.append("ALTER TABLE release_sources ADD COLUMN notes VARCHAR(1024)")
    if "source_tier" not in existing_columns:
        statements.append("ALTER TABLE release_sources ADD COLUMN source_tier INTEGER NOT NULL DEFAULT 3")
    if "preferred_method" not in existing_columns:
        statements.append("ALTER TABLE release_sources ADD COLUMN preferred_method VARCHAR(32) NOT NULL DEFAULT 'auto'")
    if "crawl_delay_seconds" not in existing_columns:
        statements.append("ALTER TABLE release_sources ADD COLUMN crawl_delay_seconds INTEGER NOT NULL DEFAULT 2")
    if "max_requests_per_hour" not in existing_columns:
        statements.append("ALTER TABLE release_sources ADD COLUMN max_requests_per_hour INTEGER NOT NULL DEFAULT 60")
    if "consecutive_failures" not in existing_columns:
        statements.append("ALTER TABLE release_sources ADD COLUMN consecutive_failures INTEGER NOT NULL DEFAULT 0")
    if "health_score" not in existing_columns:
        statements.append("ALTER TABLE release_sources ADD COLUMN health_score INTEGER NOT NULL DEFAULT 100")
    if "quarantine_until" not in existing_columns:
        statements.append("ALTER TABLE release_sources ADD COLUMN quarantine_until TIMESTAMP")
    if "last_failure_reason" not in existing_columns:
        statements.append("ALTER TABLE release_sources ADD COLUMN last_failure_reason VARCHAR(64)")
    if "last_success_at" not in existing_columns:
        statements.append("ALTER TABLE release_sources ADD COLUMN last_success_at TIMESTAMP")
    if "last_listing_etag" not in existing_columns:
        statements.append("ALTER TABLE release_sources ADD COLUMN last_listing_etag VARCHAR(255)")
    if "last_listing_modified" not in existing_columns:
        statements.append("ALTER TABLE release_sources ADD COLUMN last_listing_modified VARCHAR(255)")
    if "last_listing_checked_at" not in existing_columns:
        statements.append("ALTER TABLE release_sources ADD COLUMN last_listing_checked_at TIMESTAMP")

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))

        # Repair legacy/null data to satisfy API response contracts.
        connection.execute(text("UPDATE release_sources SET category = '' WHERE category IS NULL"))
        connection.execute(text("UPDATE release_sources SET notes = '' WHERE notes IS NULL"))
        connection.execute(text("UPDATE release_sources SET is_active = FALSE WHERE is_active IS NULL"))
        connection.execute(text("UPDATE release_sources SET source_tier = 3 WHERE source_tier IS NULL"))
        connection.execute(text("UPDATE release_sources SET preferred_method = 'auto' WHERE preferred_method IS NULL"))
        connection.execute(text("UPDATE release_sources SET crawl_delay_seconds = 2 WHERE crawl_delay_seconds IS NULL OR crawl_delay_seconds < 0"))
        connection.execute(text("UPDATE release_sources SET max_requests_per_hour = 60 WHERE max_requests_per_hour IS NULL OR max_requests_per_hour < 1"))
        connection.execute(text("UPDATE release_sources SET consecutive_failures = 0 WHERE consecutive_failures IS NULL OR consecutive_failures < 0"))
        connection.execute(text("UPDATE release_sources SET health_score = 100 WHERE health_score IS NULL OR health_score < 0"))
        connection.execute(text("UPDATE release_sources SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))
        connection.execute(text("UPDATE release_sources SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL"))


def ensure_app_migrations_table() -> None:
    """Create internal migrations tracking table if it does not exist."""
    inspector = inspect(engine)
    if "app_migrations" in inspector.get_table_names():
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE app_migrations (
                    name VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )


def _canonical_release_source_url(raw_url: str) -> str:
    """Normalize release source URLs to keep seeded entries deduplicated."""
    value = (raw_url or "").strip()
    if not value:
        return ""

    if "://" not in value:
        value = f"https://{value}"

    parsed = urlparse(value)
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or ""

    if path != "/":
        path = path.rstrip("/")

    return f"{scheme}://{netloc}{path}" if path else f"{scheme}://{netloc}"


def apply_release_source_data_migration() -> None:
    """Apply baseline release sources with cleanup, dedupe, and idempotent upsert."""
    inspector = inspect(engine)
    if "release_sources" not in inspector.get_table_names():
        return
    if "app_migrations" not in inspector.get_table_names():
        return

    with engine.begin() as connection:
        rows = connection.execute(
            text("SELECT id, company_name, category, source_url, notes, is_active FROM release_sources ORDER BY id ASC")
        ).mappings().all()

        # Deduplicate legacy rows by canonical URL, preserving the oldest record.
        kept_ids_by_canonical: dict[str, int] = {}
        duplicate_ids: list[int] = []
        for row in rows:
            canonical = _canonical_release_source_url(str(row["source_url"] or ""))
            if not canonical:
                continue
            current_id = int(row["id"])
            existing_id = kept_ids_by_canonical.get(canonical)
            if existing_id is None:
                kept_ids_by_canonical[canonical] = current_id
            else:
                duplicate_ids.append(current_id)

        if duplicate_ids:
            connection.execute(
                text("DELETE FROM release_sources WHERE id = :id"),
                [{"id": duplicate_id} for duplicate_id in duplicate_ids],
            )

        rows = connection.execute(
            text("SELECT id, source_url FROM release_sources ORDER BY id ASC")
        ).mappings().all()
        id_by_canonical: dict[str, int] = {}
        for row in rows:
            source_id = int(row["id"])
            canonical = _canonical_release_source_url(str(row["source_url"] or ""))
            if not canonical:
                continue

            existing_id = id_by_canonical.get(canonical)
            if existing_id is None:
                id_by_canonical[canonical] = source_id
                if canonical != str(row["source_url"] or ""):
                    connection.execute(
                        text(
                            """
                            UPDATE release_sources
                            SET source_url = :source_url,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = :id
                            """
                        ),
                        {"source_url": canonical, "id": source_id},
                    )
                continue

            # Safety net for collisions after normalization.
            connection.execute(text("DELETE FROM release_sources WHERE id = :id"), {"id": source_id})

        rows = connection.execute(
            text("SELECT id, source_url FROM release_sources ORDER BY id ASC")
        ).mappings().all()
        id_by_canonical = {
            _canonical_release_source_url(str(row["source_url"] or "")): int(row["id"])
            for row in rows
            if _canonical_release_source_url(str(row["source_url"] or ""))
        }

        insert_stmt = text(
            """
            INSERT INTO release_sources (company_name, category, source_url, notes, is_active, created_at, updated_at)
            VALUES (:company_name, :category, :source_url, :notes, :is_active, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
        )

        update_stmt = text(
            """
            UPDATE release_sources
            SET company_name = :company_name,
                category = :category,
                notes = :notes,
                is_active = :is_active,
                source_url = :source_url,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
            """
        )

        # Build a canonical, de-duplicated defaults map (last value wins for same URL).
        defaults_by_canonical: dict[str, dict[str, str]] = {}
        for source in DEFAULT_RELEASE_SOURCES:
            source_url = str(source.get("source_url") or "")
            company_name = str(source.get("company_name") or "").strip()
            category = str(source.get("category") or "").strip()
            notes = str(source.get("notes") or "")
            if not source_url or not company_name or not category:
                continue

            canonical = _canonical_release_source_url(source_url)
            if not canonical:
                continue
            defaults_by_canonical[canonical] = {
                "company_name": company_name,
                "category": category,
                "source_url": canonical,
                "notes": notes,
            }

        for canonical, source in defaults_by_canonical.items():
            existing_id = id_by_canonical.get(canonical)
            if existing_id is None:
                connection.execute(
                    insert_stmt,
                    {
                        "company_name": source["company_name"],
                        "category": source["category"],
                        "source_url": canonical,
                        "notes": source["notes"],
                        "is_active": True,
                    },
                )
                continue

            connection.execute(
                update_stmt,
                {
                    "id": existing_id,
                    "company_name": source["company_name"],
                    "category": source["category"],
                    "source_url": canonical,
                    "notes": source["notes"],
                    "is_active": True,
                },
            )

        connection.execute(
            text(
                """
                INSERT INTO app_migrations (name)
                VALUES (:name)
                ON CONFLICT (name) DO NOTHING
                """
            ),
            {"name": RELEASE_SOURCE_MIGRATION_NAME},
        )
