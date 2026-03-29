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
    def fake_run_daily_pipeline(db, raise_on_error=False):
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


def test_post_reports_run_articles_returns_200_with_mocked_pipeline(client):
    def fake_run_articles_pipeline(db, raise_on_error=False):
        return {"articles_found": 5, "articles_saved": 4, "report_id": 1}

    original = reports_api.run_articles_pipeline
    reports_api.run_articles_pipeline = fake_run_articles_pipeline
    try:
        response = client.post("/api/reports/run/articles")
    finally:
        reports_api.run_articles_pipeline = original

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["message"] == "Articles pipeline completed"
    assert body["articles_found"] == 5


def test_post_reports_run_releases_returns_200_with_mocked_pipeline(client):
    def fake_run_release_pipeline(db, raise_on_error=False):
        return {"releases_found": 2, "releases_saved": 2, "report_id": 1}

    original = reports_api.run_release_pipeline
    reports_api.run_release_pipeline = fake_run_release_pipeline
    try:
        response = client.post("/api/reports/run/releases")
    finally:
        reports_api.run_release_pipeline = original

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["message"] == "Releases pipeline completed"
    assert body["releases_found"] == 2


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


def test_get_reports_latest_show_all_includes_rejected_articles(client, db_session, seeded_query):
    kept_article = Article(
        title="Kept article",
        url="https://example.com/kept",
        score=8,
        kept=True,
        passed_relevance_filter=True,
        rejection_reason=None,
        matched_query_id=seeded_query.id,
    )
    rejected_article = Article(
        title="Rejected article",
        url="https://example.com/rejected",
        score=2,
        kept=False,
        passed_relevance_filter=False,
        rejection_reason="failed_relevance_filter",
        matched_query_id=seeded_query.id,
    )
    report = Report(
        report_date=datetime.date.today(),
        total_articles_found=2,
        total_articles_kept=1,
        articles=[kept_article, rejected_article],
    )
    db_session.add(report)
    db_session.commit()

    filtered = client.get("/api/reports/latest")
    show_all = client.get("/api/reports/latest?show_all=true")

    assert filtered.status_code == 200
    assert show_all.status_code == 200
    assert len(filtered.json()["articles"]) == 1
    assert len(show_all.json()["articles"]) == 2


def test_get_report_by_id_show_all_includes_rejected_articles(client, db_session, seeded_query):
    kept_article = Article(
        title="Kept article",
        url="https://example.com/kept-2",
        score=7,
        kept=True,
        passed_relevance_filter=True,
        rejection_reason=None,
        matched_query_id=seeded_query.id,
    )
    rejected_article = Article(
        title="Rejected article",
        url="https://example.com/rejected-2",
        score=3,
        kept=False,
        passed_relevance_filter=True,
        rejection_reason="score_below_threshold",
        matched_query_id=seeded_query.id,
    )
    report = Report(
        report_date=datetime.date.today(),
        total_articles_found=2,
        total_articles_kept=1,
        articles=[kept_article, rejected_article],
    )
    db_session.add(report)
    db_session.commit()
    db_session.refresh(report)

    filtered = client.get(f"/api/reports/{report.id}")
    show_all = client.get(f"/api/reports/{report.id}?show_all=true")

    assert filtered.status_code == 200
    assert show_all.status_code == 200
    assert len(filtered.json()["articles"]) == 1
    assert len(show_all.json()["articles"]) == 2


def test_post_article_feedback_supports_all_feedback_types(client, db_session, seeded_query):
    article = Article(
        title="Feedback target",
        url="https://example.com/feedback-target",
        score=6,
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
    db_session.refresh(article)

    helpful = client.post(
        f"/api/articles/{article.id}/feedback",
        json={"feedback_type": "helpful"},
    )
    too_low = client.post(
        f"/api/articles/{article.id}/feedback",
        json={"feedback_type": "score_too_low", "user_corrected_score": 8},
    )
    too_high = client.post(
        f"/api/articles/{article.id}/feedback",
        json={"feedback_type": "score_too_high", "user_corrected_score": 3},
    )

    assert helpful.status_code == 200
    assert too_low.status_code == 200
    assert too_high.status_code == 200
    assert helpful.json()["message"] == "Thank you for the feedback"
    assert too_low.json()["status"] == "success"
    assert too_high.json()["status"] == "success"


def test_post_article_feedback_validates_score_range(client, db_session, seeded_query):
    article = Article(
        title="Feedback validation target",
        url="https://example.com/feedback-validation",
        score=6,
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
    db_session.refresh(article)

    response = client.post(
        f"/api/articles/{article.id}/feedback",
        json={"feedback_type": "score_too_low", "user_corrected_score": 11},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "user_corrected_score must be between 1 and 10"
