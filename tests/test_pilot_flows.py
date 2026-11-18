from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from tests.conftest import TEST_PASSWORD


def setup_booking(api):
    customer = api.post("/api/clients", json={"name": "Cliente Piloto", "phone": "11999990010"}).json()
    service = api.post("/api/services", json={
        "name": "Avaliação", "category": "Pele", "description": "Serviço de teste",
        "price": 120, "duration_minutes": 60,
    }).json()
    professional = api.post("/api/professionals", json={"name": "Pessoa Teste", "specialty": "Pele"}).json()
    return {
        "client_id": customer["id"], "service_id": service["id"], "professional_id": professional["id"],
        "scheduled_at": "2099-05-10T14:00:00",
    }


def test_concurrent_overlap_and_snapshot_duration(client):
    booking = setup_booking(client)
    start = Barrier(2)

    def submit(hour):
        start.wait()
        return client.post("/api/appointments", json={**booking, "scheduled_at": f"2099-05-10T{hour}:00"})

    with ThreadPoolExecutor(2) as pool:
        responses = list(pool.map(submit, ["14:00", "14:30"]))
    assert sorted(response.status_code for response in responses) == [200, 409]
    reference = client.get("/api/appointments").json()[0]
    assert reference["duration_minutes"] == 60
    assert client.put(f"/api/services/{booking['service_id']}", json={"duration_minutes": 15}).status_code == 200
    appointments_after_edit = client.get("/api/appointments").json()
    assert appointments_after_edit[0]["duration_minutes"] == 60
    endpoint = f"/api/appointments/{reference['id']}"
    assert client.patch(endpoint, json={"final_price": 130, "notes": "Ficha de teste"}).json()["final_price"] == 130
    assert client.patch(endpoint + "/status", json={"status": "canceled"}).status_code == 200
    assert client.post("/api/appointments", json={**booking, "scheduled_at": reference["scheduled_at"]}).status_code == 200
    assert client.patch(endpoint + "/status", json={"status": "scheduled"}).status_code == 409


def test_agent_reschedule_confirmation_is_bound_to_account_and_state(client):
    booking = client.post("/api/appointments", json=setup_booking(client)).json()
    request = {"tool": "reschedule", "appointment_id": booking["id"], "scheduled_at": "2099-05-11T15:00:00"}
    preview = client.post("/api/agent/tools", json=request).json()
    assert preview["preview"]["previous_at"] < preview["preview"]["scheduled_at"]
    assert client.get("/api/appointments").json()[0]["scheduled_at"] == booking["scheduled_at"]
    confirmed = {**request, "confirm": True, "confirmation_token": preview["confirmation_token"]}

    other = {"name": "Outra Pessoa", "email": "staff@example.test", "password": TEST_PASSWORD, "role": "admin"}
    assert client.post("/api/auth/accounts", json=other).status_code == 201
    login = client.post("/api/auth/login", json=other).json()
    headers = {"Authorization": "Bearer " + login["access_token"]}
    password = "outra senha segura de teste"
    assert client.post("/api/auth/password", json={"current_password": TEST_PASSWORD, "new_password": password}, headers=headers).status_code == 204
    login = client.post("/api/auth/login", json={**other, "password": password}).json()
    headers["Authorization"] = "Bearer " + login["access_token"]
    assert client.post("/api/agent/tools", json=confirmed, headers=headers).json()["status"] == "invalid_confirmation"
    assert client.post("/api/agent/tools", json=confirmed).json()["status"] == "rescheduled"
    assert client.post("/api/agent/tools", json=confirmed).json()["status"] == "invalid_confirmation"


def test_reactivation_catalog_and_professionals(client):
    booking = setup_booking(client)
    for catalog, resource_id in (
        ("services", booking["service_id"]), ("professionals", booking["professional_id"]),
    ):
        endpoint = f"/api/{catalog}/{resource_id}"
        data = {"active": False}
        if catalog == "professionals":
            data.update(name="Profissional editada", specialty="Pele")
        assert client.put(endpoint, json=data).status_code == 200
        assert client.get(f"/api/{catalog}").json() == []
        assert len(client.get(f"/api/{catalog}?active_only=false").json()) == 1
        assert client.put(endpoint, json={**data, "active": True}).status_code == 200
        assert len(client.get(f"/api/{catalog}").json()) == 1


def test_demo_simulator_is_disabled_in_production(client, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    result = client.post("/api/whatsapp/simulate", json={"client_phone": "5511999999999", "message": "Agendar"})
    assert result.status_code == 404
    assert client.get("/api/clients").json() == []
