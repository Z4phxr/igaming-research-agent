def test_api_query_crud_sequence(client):
    create_response = client.post(
        "/api/queries",
        json={
            "search_term": "Colorado regulations",
            "stream_type": "legislative",
            "description": "Track changes",
            "is_active": True,
        },
    )
    assert create_response.status_code == 201
    query_id = create_response.json()["id"]

    fetch_response = client.get("/api/queries")
    assert fetch_response.status_code == 200
    assert any(item["id"] == query_id for item in fetch_response.json())

    update_response = client.put(
        f"/api/queries/{query_id}",
        json={"search_term": "Colorado regulation updates"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["search_term"] == "Colorado regulation updates"

    delete_response = client.delete(f"/api/queries/{query_id}")
    assert delete_response.status_code == 204

    final_response = client.get("/api/queries")
    assert all(item["id"] != query_id for item in final_response.json())
