from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

def create_base_records(client: TestClient) -> tuple[int, int, int]:
    suffix = str(int(datetime.now(timezone.utc).timestamp() * 1000))

    client_response = client.post(
        "/api/clients",
        json={
            "name": f"Cliente Teste {suffix}",
            "phone": f"119{suffix[-8:]}",
            "email": f"cliente{suffix}@teste.com",
            "hair_type": "Ondulado",
            "skin_type": "Mista",
            "interests": "cabelo hidratação beleza",
            "notes": "Criado em teste automatizado.",
        },
    )
    assert client_response.status_code == 200

    service_response = client.post(
        "/api/services",
        json={
            "name": f"Hidratação Teste {suffix}",
            "category": "Cabelo",
            "description": "Serviço criado para teste automatizado.",
            "duration_minutes": 60,
            "price": 120.0,
            "tags": "cabelo hidratação teste",
        },
    )
    assert service_response.status_code == 200

    professional_response = client.post(
        "/api/professionals",
        json={"name": f"Profissional Teste {suffix}", "specialty": "Cabelo"},
    )
    assert professional_response.status_code == 200

    return (
        client_response.json()["id"],
        service_response.json()["id"],
        professional_response.json()["id"],
    )


def test_create_appointment_flow(client: TestClient) -> None:
    client_id, service_id, professional_id = create_base_records(client)
    response = client.post(
        "/api/appointments",
        json={
            "client_id": client_id,
            "service_id": service_id,
            "professional_id": professional_id,
            # The Streamlit form sends a local ISO timestamp without a timezone.
            "scheduled_at": (datetime.now() + timedelta(days=3)).isoformat(),
            "final_price": 120.0,
            "notes": "Teste de criação de agendamento.",
        },
    )
    assert response.status_code == 200
    assert response.json()["client_id"] == client_id


def test_whatsapp_simulation_flow(client: TestClient) -> None:
    create_base_records(client)
    response = client.post(
        "/api/whatsapp/simulate",
        json={
            "client_name": "Cliente WhatsApp",
            "client_phone": "11988887777",
            "message": "Oi, tem horário amanhã para hidratação às 14h?",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert "intent" in payload
    assert "response" in payload
    assert "action_status" in payload
    assert "action_suggested" in payload


def test_campaign_simulation_flow(client: TestClient) -> None:
    create_base_records(client)
    campaign_response = client.post(
        "/api/campaigns",
        json={
            "title": "Campanha Teste",
            "message": "Mensagem de campanha criada em teste.",
            "target_audience": "cabelo",
            "scheduled_at": (datetime.now() + timedelta(days=1)).isoformat(),
            "status": "scheduled",
        },
    )
    assert campaign_response.status_code == 200

    campaign_id = campaign_response.json()["id"]
    send_response = client.post(f"/api/campaigns/{campaign_id}/simulate-send")
    assert send_response.status_code == 200
    assert "created" in send_response.json()
