import datetime

from sqlalchemy.exc import IntegrityError

from app.models import Article, Query, Report


def test_query_model_creation(db_session):
    query = Query(
        search_term="New Jersey iGaming",
        stream_type="business",
        description="Monitor operator partnerships",
        is_active=True,
    )

    db_session.add(query)
    db_session.commit()
    db_session.refresh(query)

    assert query.id is not None
    assert query.created_at is not None
    assert query.updated_at is not None


def test_article_model_creation_with_query_relation(db_session, seeded_query):
    article = Article(
        title="State expands online casino access",
        url="https://example.com/igaming-story",
        source_domain="example.com",
        summary="Key legislation changes announced.",
        full_text="Long text" * 100,
        score=8,
        tags="legislation,market",
        matched_query_id=seeded_query.id,
        published_date=datetime.datetime.utcnow(),
    )

    db_session.add(article)
    db_session.commit()
    db_session.refresh(article)

    assert article.id is not None
    assert article.matched_query_id == seeded_query.id
    assert article.matched_query is not None


def test_report_model_creation_with_articles(db_session, seeded_query):
    article = Article(
        title="US iGaming policy shift",
        url="https://example.com/policy-shift",
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
    db_session.refresh(report)

    assert report.id is not None
    assert len(report.articles) == 1
    assert report.articles[0].url == "https://example.com/policy-shift"


def test_article_requires_unique_url(db_session, seeded_query):
    first = Article(
        title="A",
        url="https://example.com/duplicate",
        matched_query_id=seeded_query.id,
    )
    second = Article(
        title="B",
        url="https://example.com/duplicate",
        matched_query_id=seeded_query.id,
    )

    db_session.add(first)
    db_session.commit()

    db_session.add(second)
    try:
        db_session.commit()
        assert False, "Expected IntegrityError for duplicate URL"
    except IntegrityError:
        db_session.rollback()
