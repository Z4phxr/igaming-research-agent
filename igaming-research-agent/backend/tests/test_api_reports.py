import datetime

from app.models import Article, Report
from app.api import reports as reports_api


def test_get_reports_returns_summaries(client, db_session, seeded_query):
    article = Article(
        title="Article in report",
        url="https://example.com/report-article",
        score=7,
        matched_query_id=seeded_query.id,
    )
    report = Report(
        report_date=datetime.date.today(),
        total_articles_found=1,
        total_articles_kept=1,
        articles=[article],
    )
    db_session.add(report)
    db_session.commit()

    response = client.get("/api/reports")

    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert "articles" not in response.json()[0]


def test_get_report_by_id_returns_full_payload(client, db_session, seeded_query):
    article = Article(
        title="Detailed article",
        url="https://example.com/detailed-report",
        score=8,
        matched_query_id=seeded_query.id,
    )
    report = Report(
        report_date=datetime.date.today(),
        total_articles_found=2,
        total_articles_kept=1,
        articles=[article],
    )
    db_session.add(report)
    db_session.commit()
    db_session.refresh(report)

    response = client.get(f"/api/reports/{report.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == report.id
    assert len(body["articles"]) == 1
    assert body["articles"][0]["url"] == "https://example.com/detailed-report"


def test_post_reports_run_returns_200_with_mocked_pipeline(client, db_session):
    def fake_run_daily_pipeline(db):
        report = Report(
            report_date=datetime.date.today(),
            total_articles_found=3,
            total_articles_kept=2,
        )
        db.add(report)
        db.commit()

    original = reports_api.run_daily_pipeline
    reports_api.run_daily_pipeline = fake_run_daily_pipeline
    try:
        response = client.post("/api/reports/run")
    finally:
        reports_api.run_daily_pipeline = original

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["message"] == "Pipeline completed"
    assert body["articles_found"] == 3


def test_get_reports_latest_returns_most_recent_report(client, db_session):
    older = Report(
        report_date=datetime.date(2026, 3, 20),
        total_articles_found=2,
        total_articles_kept=1,
    )
    newer = Report(
        report_date=datetime.date(2026, 3, 22),
        total_articles_found=5,
        total_articles_kept=3,
    )
    db_session.add_all([older, newer])
    db_session.commit()

    response = client.get("/api/reports/latest")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == newer.id
    assert body["report_date"] == "2026-03-22"


def test_get_reports_latest_returns_404_when_no_reports_exist(client):
    response = client.get("/api/reports/latest")

    assert response.status_code == 404
    assert response.json()["detail"] == "No reports found"
