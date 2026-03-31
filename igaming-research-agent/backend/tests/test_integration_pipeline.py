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
    assert article.rejection_reason == "Rejected: fail to check the date"
    assert article.kept is False
    assert article.published_date is None
    verify.close()


def test_pipeline_accepts_relative_published_date(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    test_session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(scheduler, "SessionLocal", test_session_local)
    monkeypatch.setattr(
        scheduler,
        "run_search_pipeline",
        lambda db: [
            {
                "title": "Relative date item",
                "url": "https://example.com/relative-date",
                "snippet": "x",
                "published_date": "2 hours ago",
            }
        ],
    )
    monkeypatch.setattr(
        scheduler,
        "scrape_articles",
        lambda articles: [{**articles[0], "full_text": "Article body " * 50, "source_domain": "example.com"}],
    )

    called = {"analyze": 0}

    def fake_run_analysis_pipeline(articles):
        called["analyze"] += 1
        assert len(articles) == 1
        return {
            "final_articles": [
                {
                    **articles[0],
                    "score": 7,
                    "raw_score": 7,
                    "summary": "Relevant summary",
                    "tags": "regulation",
                    "passed_relevance_filter": True,
                    "kept": True,
                    "rejection_reason": None,
                }
            ],
            "all_articles": [
                {
                    **articles[0],
                    "score": 7,
                    "raw_score": 7,
                    "summary": "Relevant summary",
                    "tags": "regulation",
                    "passed_relevance_filter": True,
                    "kept": True,
                    "rejection_reason": None,
                }
            ],
        }

    monkeypatch.setattr(scheduler, "run_analysis_pipeline", fake_run_analysis_pipeline)

    scheduler.run_daily_pipeline()

    verify = test_session_local()
    report = verify.query(scheduler.Report).first()
    article = verify.query(scheduler.Article).first()

    assert called["analyze"] == 1
    assert report is not None
    assert report.total_articles_found == 1
    assert report.total_articles_kept == 1
    assert article is not None
    assert article.rejection_reason is None
    assert article.kept is True
    assert article.published_date is not None
    verify.close()


def test_pipeline_infers_published_date_from_url_when_missing_provider_date(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    test_session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(scheduler, "SessionLocal", test_session_local)
    path_date = datetime.datetime.utcnow().strftime("%Y/%m/%d")
    monkeypatch.setattr(
        scheduler,
        "run_search_pipeline",
        lambda db: [
            {
                "title": "URL dated item",
                "url": f"https://example.com/news/{path_date}/policy-update",
                "snippet": "x",
            }
        ],
    )
    monkeypatch.setattr(
        scheduler,
        "scrape_articles",
        lambda articles: [{**articles[0], "full_text": "Article body " * 50, "source_domain": "example.com"}],
    )

    called = {"analyze": 0}

    def fake_run_analysis_pipeline(articles):
        called["analyze"] += 1
        assert len(articles) == 1
        assert isinstance(articles[0].get("published_date"), datetime.datetime)
        return {
            "final_articles": [
                {
                    **articles[0],
                    "score": 7,
                    "raw_score": 7,
                    "summary": "Relevant summary",
                    "tags": "regulation",
                    "passed_relevance_filter": True,
                    "kept": True,
                    "rejection_reason": None,
                }
            ],
            "all_articles": [
                {
                    **articles[0],
                    "score": 7,
                    "raw_score": 7,
                    "summary": "Relevant summary",
                    "tags": "regulation",
                    "passed_relevance_filter": True,
                    "kept": True,
                    "rejection_reason": None,
                }
            ],
        }

    monkeypatch.setattr(scheduler, "run_analysis_pipeline", fake_run_analysis_pipeline)

    scheduler.run_daily_pipeline()

    verify = test_session_local()
    report = verify.query(scheduler.Report).first()
    article = verify.query(scheduler.Article).first()

    assert called["analyze"] == 1
    assert report is not None
    assert report.total_articles_found == 1
    assert report.total_articles_kept == 1
    assert article is not None
    assert article.rejection_reason is None
    assert article.kept is True
    assert article.published_date is not None
    verify.close()


def test_pipeline_does_not_call_llm_date_fallback_when_provider_date_exists(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    test_session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(scheduler, "SessionLocal", test_session_local)
    recent_date = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    monkeypatch.setattr(
        scheduler,
        "run_search_pipeline",
        lambda db: [
            {
                "title": "Has provider date",
                "url": "https://example.com/provider-date",
                "snippet": "x",
                "published_date": recent_date,
            }
        ],
    )
    monkeypatch.setattr(
        scheduler,
        "scrape_articles",
        lambda articles: [{**articles[0], "full_text": "Article body " * 50, "source_domain": "example.com"}],
    )

    llm_calls = {"count": 0}

    def fake_llm_date_fallback(article, now_utc=None, db=None):
        llm_calls["count"] += 1
        return None

    monkeypatch.setattr(scheduler, "infer_published_date_with_llm", fake_llm_date_fallback)

    def fake_run_analysis_pipeline(articles):
        assert len(articles) == 1
        assert articles[0].get("date_inference_source") == "provider"
        return {
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
        }

    monkeypatch.setattr(scheduler, "run_analysis_pipeline", fake_run_analysis_pipeline)

    scheduler.run_daily_pipeline()

    assert llm_calls["count"] == 0


def test_pipeline_calls_llm_date_fallback_only_when_date_not_discovered(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    test_session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(scheduler, "SessionLocal", test_session_local)
    monkeypatch.setattr(
        scheduler,
        "run_search_pipeline",
        lambda db: [
            {
                "title": "LLM fallback date",
                "url": "https://example.com/no-date-found",
                "snippet": "x",
            }
        ],
    )
    monkeypatch.setattr(
        scheduler,
        "scrape_articles",
        lambda articles: [{**articles[0], "full_text": "No deterministic date in this content.", "source_domain": "example.com"}],
    )

    llm_calls = {"count": 0}

    def fake_llm_date_fallback(article, now_utc=None, db=None):
        llm_calls["count"] += 1
        return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    monkeypatch.setattr(scheduler, "infer_published_date_with_llm", fake_llm_date_fallback)

    def fake_run_analysis_pipeline(articles):
        assert len(articles) == 1
        assert articles[0].get("date_inference_source") == "llm"
        return {
            "final_articles": [
                {
                    **articles[0],
                    "score": 7,
                    "raw_score": 7,
                    "summary": "Relevant summary",
                    "tags": "regulation",
                    "passed_relevance_filter": True,
                    "kept": True,
                    "rejection_reason": None,
                }
            ],
            "all_articles": [
                {
                    **articles[0],
                    "score": 7,
                    "raw_score": 7,
                    "summary": "Relevant summary",
                    "tags": "regulation",
                    "passed_relevance_filter": True,
                    "kept": True,
                    "rejection_reason": None,
                }
            ],
        }

    monkeypatch.setattr(scheduler, "run_analysis_pipeline", fake_run_analysis_pipeline)

    scheduler.run_daily_pipeline()

    verify = test_session_local()
    report = verify.query(scheduler.Report).first()
    article = verify.query(scheduler.Article).first()

    assert llm_calls["count"] == 1
    assert report is not None
    assert report.total_articles_found == 1
    assert report.total_articles_kept == 1
    assert article is not None
    assert article.published_date is not None
    verify.close()
