import datetime

from app.models import Article, Query


def test_database_session_crud_cycle(db_session):
    query = Query(
        search_term="Pennsylvania iGaming",
        stream_type="whitelist",
        description="Operator whitelist updates",
        is_active=True,
        created_at=datetime.datetime.utcnow(),
        updated_at=datetime.datetime.utcnow(),
    )

    db_session.add(query)
    db_session.commit()
    db_session.refresh(query)

    assert query.id is not None

    fetched = db_session.get(Query, query.id)
    assert fetched is not None
    assert fetched.search_term == "Pennsylvania iGaming"

    fetched.description = "Updated"
    db_session.commit()

    updated = db_session.get(Query, query.id)
    assert updated is not None
    assert updated.description == "Updated"

    db_session.delete(updated)
    db_session.commit()

    assert db_session.get(Query, query.id) is None


def test_database_article_insert_and_lookup(db_session, seeded_query):
    article = Article(
        title="Market growth update",
        url="https://example.com/market-growth",
        score=9,
        matched_query_id=seeded_query.id,
    )
    db_session.add(article)
    db_session.commit()

    stored = db_session.query(Article).filter(Article.url == "https://example.com/market-growth").first()
    assert stored is not None
    assert stored.score == 9
