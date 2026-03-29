import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.services import scheduler


def test_full_pipeline_saves_analyzed_article(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    test_session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(scheduler, "SessionLocal", test_session_local)
    recent_date = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    monkeypatch.setattr(
        scheduler,
        "run_search_pipeline",
        lambda db: [{"title": "Policy update", "url": "https://example.com/news", "snippet": "x", "published_date": recent_date}],
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
    assert article.published_date is not None
    assert article.rejection_reason is None
    verify.close()


def test_pipeline_rejects_article_missing_published_date(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    test_session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(scheduler, "SessionLocal", test_session_local)
    monkeypatch.setattr(
        scheduler,
        "run_search_pipeline",
        lambda db: [{"title": "No date", "url": "https://example.com/no-date", "snippet": "x"}],
    )
    monkeypatch.setattr(
        scheduler,
        "scrape_articles",
        lambda articles: [{**articles[0], "full_text": "Article body " * 50, "source_domain": "example.com"}],
    )

    called = {"analyze": 0}

    def fake_run_analysis_pipeline(articles):
        called["analyze"] += 1
        assert articles == []
        return {"final_articles": [], "all_articles": []}

    monkeypatch.setattr(scheduler, "run_analysis_pipeline", fake_run_analysis_pipeline)

    scheduler.run_daily_pipeline()

    verify = test_session_local()
    report = verify.query(scheduler.Report).first()
    article = verify.query(scheduler.Article).first()

    assert called["analyze"] == 1
    assert report is not None
    assert report.total_articles_found == 1
    assert report.total_articles_kept == 0
    assert article is not None
    assert article.rejection_reason == "missing_published_date"
    assert article.kept is False
    assert article.published_date is None
    verify.close()
