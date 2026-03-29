import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.services import scheduler


class FakeScheduler:
    def __init__(self):
        self.running = False
        self.jobs = []
        self.shutdown_called = False

    def add_job(self, fn, trigger, id, replace_existing):
        self.jobs.append({"fn": fn, "id": id, "replace_existing": replace_existing, "trigger": trigger})

    def start(self):
        self.running = True

    def shutdown(self, wait=False):
        self.shutdown_called = True
        self.running = False


def test_scheduler_start_and_stop_registers_job(monkeypatch):
    fake = FakeScheduler()
    monkeypatch.setattr(scheduler, "_scheduler", fake)

    scheduler.start_scheduler()

    assert fake.running is True
    assert len(fake.jobs) == 2
    job_ids = {job["id"] for job in fake.jobs}
    assert job_ids == {"daily_articles_pipeline", "daily_releases_pipeline"}

    scheduler.stop_scheduler()
    assert fake.shutdown_called is True


def test_scheduler_pipeline_calls_services_in_order(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    test_session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    calls = []

    monkeypatch.setattr(scheduler, "SessionLocal", test_session_local)

    def fake_run_search_pipeline(db):
        calls.append("search")
        return [
            {
                "title": "Story",
                "url": "https://example.com/story",
                "snippet": "x",
                "published_date": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            }
        ]

    def fake_scrape_articles(articles):
        calls.append("scrape")
        return [{**articles[0], "full_text": "content" * 100, "source_domain": "example.com"}]

    def fake_run_analysis_pipeline(articles):
        calls.append("analyze")
        analyzed = {
            **articles[0],
            "score": 9,
            "raw_score": 9,
            "summary": "Good",
            "tags": "market",
            "passed_relevance_filter": True,
            "kept": True,
            "rejection_reason": None,
        }
        return {"final_articles": [analyzed], "all_articles": [analyzed]}

    monkeypatch.setattr(scheduler, "run_search_pipeline", fake_run_search_pipeline)
    monkeypatch.setattr(scheduler, "scrape_articles", fake_scrape_articles)
    monkeypatch.setattr(scheduler, "run_analysis_pipeline", fake_run_analysis_pipeline)

    scheduler.run_daily_pipeline()

    assert calls == ["search", "scrape", "analyze"]
