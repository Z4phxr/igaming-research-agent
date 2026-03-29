def test_release_source_crud_flow(client):
    created = client.post(
        "/api/release-sources",
        json={
            "company_name": "IGT",
            "source_url": "https://www.igt.com/explore-igt/news/news",
            "is_active": True,
        },
    )

    assert created.status_code == 201
    body = created.json()
    assert body["company_name"] == "IGT"
    assert body["is_active"] is True

    listing = client.get("/api/release-sources")
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    source_id = body["id"]
    updated = client.put(f"/api/release-sources/{source_id}", json={"is_active": False})
    assert updated.status_code == 200
    assert updated.json()["is_active"] is False

    deleted = client.delete(f"/api/release-sources/{source_id}")
    assert deleted.status_code == 204

    listing_after = client.get("/api/release-sources")
    assert listing_after.status_code == 200
    assert listing_after.json() == []


def test_release_source_rejects_duplicates(client):
    payload = {
        "company_name": "IGT",
        "source_url": "https://www.igt.com/explore-igt/news/news",
        "is_active": True,
    }

    first = client.post("/api/release-sources", json=payload)
    second = client.post("/api/release-sources", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "Release source already exists"
