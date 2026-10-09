# Integration tests for the /api/v1/domains endpoints, via the FastAPI TestClient.
def test_create_and_get_domain(client):
    response = client.post(
        "/api/v1/domains", json={"name": "example.uz", "url": "https://example.uz"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "example.uz"
    assert body["is_active"] is True

    get_response = client.get(f"/api/v1/domains/{body['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "example.uz"


def test_create_domain_duplicate_returns_409(client):
    payload = {"name": "example.uz", "url": "https://example.uz"}
    client.post("/api/v1/domains", json=payload)

    response = client.post("/api/v1/domains", json=payload)

    assert response.status_code == 409


def test_get_missing_domain_returns_404(client):
    response = client.get("/api/v1/domains/999")
    assert response.status_code == 404


def test_list_and_delete_domain(client):
    created = client.post(
        "/api/v1/domains", json={"name": "example.uz", "url": "https://example.uz"}
    ).json()

    list_response = client.get("/api/v1/domains")
    assert len(list_response.json()) == 1

    delete_response = client.delete(f"/api/v1/domains/{created['id']}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/v1/domains/{created['id']}").status_code == 404
