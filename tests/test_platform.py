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
