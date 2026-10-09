from __future__ import annotations


def test_agent_lists_services(client):
    response = client.post("/api/agent/tools", json={"tool": "list_services"})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_agent_requires_confirmation_before_booking(client):
    customer = client.post("/api/clients", json={"name": "Cliente Agente", "phone": "11999998888"}).json()
    service = client.post("/api/services", json={
        "name": "Hidratacao IA", "category": "Cabelo",
        "description": "Hidratacao profissional", "duration_minutes": 60, "price": 150,
    }).json()
    professional = client.post("/api/professionals", json={
        "name": "Profissional IA", "specialty": "Cabelo",
    }).json()
    payload = {
        "tool": "book",
        "client_id": customer["id"],
        "service_id": service["id"],
        "professional_id": professional["id"],
        "scheduled_at": "2099-02-20T14:00:00",
    }
    preview = client.post("/api/agent/tools", json=payload)
    assert preview.status_code == 200
    assert preview.json()["status"] == "confirmation_required"
    assert client.get("/api/appointments").json() == []

    payload["confirm"] = True
    assert client.post("/api/agent/tools", json=payload).json()["status"] == "invalid_confirmation"
    payload["confirmation_token"] = preview.json()["confirmation_token"]
    booked = client.post("/api/agent/tools", json=payload)
    assert booked.status_code == 200
    assert booked.json()["status"] == "created"
    appointment_id = booked.json()["appointment_id"]
    assert client.post("/api/agent/tools", json=payload).json()["status"] == "unavailable"

    cancel_preview = client.post("/api/agent/tools", json={
        "tool": "cancel", "appointment_id": appointment_id,
    })
    assert cancel_preview.json()["status"] == "confirmation_required"

    cancel = client.post("/api/agent/tools", json={
        "tool": "cancel", "appointment_id": appointment_id, "confirm": True,
        "confirmation_token": cancel_preview.json()["confirmation_token"],
    })
    assert cancel.json()["status"] == "canceled"


def test_confirmation_cannot_be_used_for_another_action(client):
    customer = client.post("/api/clients", json={"name": "Outro Cliente", "phone": "11911118888"}).json()
    service = client.post("/api/services", json={
        "name": "Tratamento facial", "category": "Pele",
        "description": "Procedimento de pele", "price": 100,
    }).json()
    professional = client.post("/api/professionals", json={
        "name": "Profissional Facial", "specialty": "Pele",
    }).json()
    payload = {"tool": "book", "client_id": customer["id"],
               "service_id": service["id"], "professional_id": professional["id"],
               "scheduled_at": "2099-05-11T14:00:00"}
    preview = client.post("/api/agent/tools", json=payload).json()
    payload.update(confirm=True, confirmation_token=preview["confirmation_token"])
    altered = dict(payload, scheduled_at="2099-05-11T15:00:00")
    result = client.post("/api/agent/tools", json=altered)
    assert result.json()["status"] == "invalid_confirmation"
    assert client.get("/api/appointments").json() == []
