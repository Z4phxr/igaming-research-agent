"""Database setup for SQLAlchemy connection/session management.

TODO: Replace metadata create_all with migration-based schema management.
"""

import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

RELEASE_SOURCE_MIGRATION_NAME = "2026_03_29_release_sources_baseline"

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
        "source_url": "https://gamingcontrolboard.pa.gov/news-media/press-releases",
        "notes": "PA - drugi najwiekszy rynek",
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

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))

        # Repair legacy/null data to satisfy API response contracts.
        connection.execute(text("UPDATE release_sources SET category = '' WHERE category IS NULL"))
        connection.execute(text("UPDATE release_sources SET notes = '' WHERE notes IS NULL"))
        connection.execute(text("UPDATE release_sources SET is_active = FALSE WHERE is_active IS NULL"))
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


def apply_release_source_data_migration() -> None:
    """Apply one-time data migration that inserts baseline release sources."""
    inspector = inspect(engine)
    if "release_sources" not in inspector.get_table_names():
        return
    if "app_migrations" not in inspector.get_table_names():
        return

    with engine.begin() as connection:
        existing_count = connection.execute(text("SELECT COUNT(*) FROM release_sources")).scalar() or 0
        already_applied = connection.execute(
            text("SELECT 1 FROM app_migrations WHERE name = :name LIMIT 1"),
            {"name": RELEASE_SOURCE_MIGRATION_NAME},
        ).scalar()

        # Self-heal: if migration marker exists but table is empty, repopulate defaults.
        if already_applied and existing_count > 0:
            return

        insert_stmt = text(
            """
            INSERT INTO release_sources (company_name, category, source_url, notes, is_active, created_at, updated_at)
            VALUES (:company_name, :category, :source_url, :notes, :is_active, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
        )

        exists_stmt = text("SELECT 1 FROM release_sources WHERE source_url = :source_url LIMIT 1")
        for source in DEFAULT_RELEASE_SOURCES:
            exists = connection.execute(exists_stmt, {"source_url": source["source_url"]}).scalar()
            if exists:
                continue

            connection.execute(
                insert_stmt,
                {
                    "company_name": source["company_name"],
                    "category": source["category"],
                    "source_url": source["source_url"],
                    "notes": source["notes"],
                    "is_active": True,
                },
            )

        if not already_applied:
            connection.execute(
                text("INSERT INTO app_migrations (name) VALUES (:name)"),
                {"name": RELEASE_SOURCE_MIGRATION_NAME},
            )
