from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient


def create_records(client: TestClient) -> tuple[int, int, int]:
    suffix = "scheduling-v2"

    client_response = client.post(
        "/api/clients",
        json={
            "name": "Cliente Agenda",
            "phone": "11999998888",
            "email": "agenda@teste.com",
            "interests": "cabelo hidratacao",
        },
    )
    assert client_response.status_code == 200

    service_response = client.post(
        "/api/services",
        json={
            "name": "Hidratacao Agenda",
            "category": "Cabelo",
            "description": "Servico para validar conflitos de agenda.",
            "duration_minutes": 60,
            "price": 150.0,
            "tags": "cabelo hidratacao",
        },
    )
    assert service_response.status_code == 200

    professional_response = client.post(
        "/api/professionals",
        json={
            "name": "Profissional Agenda",
            "specialty": "Cabelo e tratamentos",
        },
    )
    assert professional_response.status_code == 200

    return (
        client_response.json()["id"],
        service_response.json()["id"],
        professional_response.json()["id"],
    )


def test_rejects_overlapping_appointments(client: TestClient) -> None:
    client_id, service_id, professional_id = create_records(client)

    first = client.post(
        "/api/appointments",
        json={
            "client_id": client_id,
            "service_id": service_id,
            "professional_id": professional_id,
            "scheduled_at": "2099-01-15T14:00:00",
        },
    )
    assert first.status_code == 200

    overlapping = client.post(
        "/api/appointments",
        json={
            "client_id": client_id,
            "service_id": service_id,
            "professional_id": professional_id,
            "scheduled_at": "2099-01-15T14:30:00",
        },
    )
    assert overlapping.status_code == 409
    assert "conflita" in overlapping.json()["detail"].lower()


def test_availability_excludes_conflicting_slots(client: TestClient) -> None:
    client_id, service_id, professional_id = create_records(client)

    created = client.post(
        "/api/appointments",
        json={
            "client_id": client_id,
            "service_id": service_id,
            "professional_id": professional_id,
            "scheduled_at": "2099-01-15T14:00:00",
        },
    )
    assert created.status_code == 200

    response = client.get(
        "/api/appointments/availability",
        params={
            "professional_id": professional_id,
            "service_id": service_id,
            "target_date": date(2099, 1, 15).isoformat(),
        },
    )
    assert response.status_code == 200
    slots = response.json()["slots"]

    assert not any("14:00:00" in slot for slot in slots)
    assert not any("14:30:00" in slot for slot in slots)
    assert any("15:00:00" in slot for slot in slots)


def test_reschedule_updates_existing_appointment(client: TestClient) -> None:
    client_id, service_id, professional_id = create_records(client)

    created = client.post(
        "/api/appointments",
        json={
            "client_id": client_id,
            "service_id": service_id,
            "professional_id": professional_id,
            "scheduled_at": "2099-01-15T10:00:00",
        },
    )
    assert created.status_code == 200
    appointment_id = created.json()["id"]

    response = client.patch(
        f"/api/appointments/{appointment_id}/reschedule",
        json={"scheduled_at": "2099-01-15T16:00:00"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "scheduled"
    assert response.json()["scheduled_at"].startswith("2099-01-15T19:00:00")


def test_rejects_appointment_outside_business_hours(client: TestClient) -> None:
    client_id, service_id, professional_id = create_records(client)

    response = client.post(
        "/api/appointments",
        json={
            "client_id": client_id,
            "service_id": service_id,
            "professional_id": professional_id,
            "scheduled_at": "2099-01-15T18:30:00",
        },
    )
    assert response.status_code == 409
    assert "horário de funcionamento" in response.json()["detail"]
