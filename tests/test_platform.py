from __future__ import annotations

def test_crm_empty(client):
    response = client.get("/api/crm/summary")
    assert response.status_code == 200
    assert response.json()["total_clients"] == 0
    assert response.json()["customers"] == []


def test_crm_uses_completed_only(client):
    person = client.post("/api/clients", json={"name":"Pessoa Teste","phone":"11999990001"})
    assert person.status_code == 200
    summary = client.get("/api/crm/summary").json()
    assert summary["total_clients"] == 1
    assert summary["customers"][0]["total_spent"] == 0
    assert summary["customers"][0]["completed_visits"] == 0


def test_api_token(client, monkeypatch):
    monkeypatch.setenv("API_ACCESS_TOKEN", "test-api-key")
    assert client.get("/api/clients").status_code == 401
    assert client.get("/api/clients", headers={"X-API-Key": "test-api-key"}).status_code == 200


def test_production_fails_closed(client, monkeypatch):
    monkeypatch.delenv("API_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    assert client.get("/api/clients").status_code == 503
