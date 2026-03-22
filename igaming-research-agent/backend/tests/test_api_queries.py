def test_get_queries_returns_list(client):
    response = client.get("/api/queries")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_post_queries_creates_query(client):
    payload = {
        "search_term": "US iGaming merger activity",
        "stream_type": "business",
        "description": "Track M&A",
        "is_active": True,
    }

    response = client.post("/api/queries", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["search_term"] == payload["search_term"]


def test_put_queries_updates_query(client):
    create_response = client.post(
        "/api/queries",
        json={
            "search_term": "Initial",
            "stream_type": "legislative",
            "description": "Old",
            "is_active": True,
        },
    )
    query_id = create_response.json()["id"]

    response = client.put(
        f"/api/queries/{query_id}",
        json={"search_term": "Updated term", "stream_type": "whitelist"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["search_term"] == "Updated term"
    assert body["stream_type"] == "whitelist"


def test_delete_queries_removes_query(client):
    create_response = client.post(
        "/api/queries",
        json={
            "search_term": "Delete me",
            "stream_type": "business",
            "description": "temp",
            "is_active": True,
        },
    )
    query_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/queries/{query_id}")
    list_response = client.get("/api/queries")

    assert delete_response.status_code == 204
    assert all(item["id"] != query_id for item in list_response.json())
