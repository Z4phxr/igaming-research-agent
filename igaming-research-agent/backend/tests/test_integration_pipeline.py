from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.services import scheduler


def test_full_pipeline_saves_analyzed_article(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    test_session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(scheduler, "SessionLocal", test_session_local)
    monkeypatch.setattr(
        scheduler,
        "run_search_pipeline",
        lambda db: [{"title": "Policy update", "url": "https://example.com/news", "snippet": "x", "published_date": "2026-03-22"}],
    )
    monkeypatch.setattr(
        scheduler,
        "scrape_articles",
        lambda articles: [{**articles[0], "full_text": "Article body " * 50, "source_domain": "example.com"}],
    )
    monkeypatch.setattr(
        scheduler,
        "run_analysis_pipeline",
        lambda articles: {
            "final_articles": [
                {
                    **articles[0],
                    "score": 8,
                    "raw_score": 8,
                    "summary": "Relevant",
                    "tags": "legislation",
                    "passed_relevance_filter": True,
                    "kept": True,
                    "rejection_reason": None,
                }
            ],
            "all_articles": [
                {
                    **articles[0],
                    "score": 8,
                    "raw_score": 8,
                    "summary": "Relevant",
                    "tags": "legislation",
                    "passed_relevance_filter": True,
                    "kept": True,
                    "rejection_reason": None,
                }
            ],
        },
    )

    scheduler.run_daily_pipeline()

    verify = test_session_local()
    report = verify.query(scheduler.Report).first()
    article = verify.query(scheduler.Article).first()

    assert report is not None
    assert report.total_articles_found == 1
    assert report.total_articles_kept == 1
    assert article is not None
    assert article.summary == "Relevant"
    verify.close()
