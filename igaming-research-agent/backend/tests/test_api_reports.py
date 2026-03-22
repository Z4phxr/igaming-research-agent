import datetime

from app.models import Article, Report


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
