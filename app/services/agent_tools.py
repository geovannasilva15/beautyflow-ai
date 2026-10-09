from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.db.models import Appointment, AppointmentStatus, Client, Professional, Service
from app.services.appointment_service import appointment_slot_error, get_available_slots
from app.core.time import utc_to_business


class AgentToolRequest(BaseModel):
    tool: Literal["list_services", "find_client", "availability", "book", "cancel"]
    client_id: int | None = None
    service_id: int | None = None
    professional_id: int | None = None
    appointment_id: int | None = None
    scheduled_at: datetime | None = None
    query: str | None = Field(default=None, max_length=120)
    confirm: bool = False


def execute_agent_tool(session: Session, request: AgentToolRequest) -> dict:
    """Auditable deterministic tools; LLM-generated actions must never bypass confirmation."""
    if request.tool == "list_services":
        services = session.exec(select(Service).where(Service.active == True)).all()  # noqa: E712
        return {"tool": request.tool, "status": "ok", "data": [
            {"id": s.id, "name": s.name, "price": s.price, "duration_minutes": s.duration_minutes}
            for s in services
        ]}

    if request.tool == "find_client":
        if not request.query:
            return {"tool": request.tool, "status": "missing_input", "message": "Informe o nome da cliente."}
        clients = session.exec(select(Client)).all()
        matches = [c for c in clients if request.query.casefold() in c.name.casefold()]
        return {"tool": request.tool, "status": "ok", "data": [
            {"id": c.id, "name": c.name} for c in matches[:10]
        ]}

    if request.tool == "availability":
        if not all([request.professional_id, request.service_id, request.scheduled_at]):
            return {"tool": request.tool, "status": "missing_input", "message": "Informe serviço, profissional e data."}
        professional = session.get(Professional, request.professional_id)
        service = session.get(Service, request.service_id)
        if not professional or not professional.active or not service or not service.active:
            return {"tool": request.tool, "status": "not_found"}
        target = request.scheduled_at.date()
        slots = get_available_slots(session, professional.id, service.id, target)
        return {"tool": request.tool, "status": "ok", "slots": [s.isoformat() for s in slots]}

    if request.tool == "book":
        if not all([request.client_id, request.service_id, request.professional_id, request.scheduled_at]):
            return {"tool": request.tool, "status": "missing_input", "message": "Informe cliente, serviço, profissional e horário."}
        client = session.get(Client, request.client_id)
        service = session.get(Service, request.service_id)
        professional = session.get(Professional, request.professional_id)
        if not client or not service or not service.active or not professional or not professional.active:
            return {"tool": request.tool, "status": "not_found"}
        from app.core.time import local_datetime_to_utc
        start = local_datetime_to_utc(request.scheduled_at)
        error = appointment_slot_error(session, professional.id, service.id, start)
        if error:
            return {"tool": request.tool, "status": "unavailable", "message": error}
        preview = {
            "client": client.name,
            "service": service.name,
            "professional": professional.name,
            "scheduled_at": utc_to_business(start).isoformat(),
            "price": service.price,
        }
        if not request.confirm:
            return {"tool": request.tool, "status": "confirmation_required", "preview": preview}
        booking = Appointment(
            client_id=client.id,
            service_id=service.id,
            professional_id=professional.id,
            scheduled_at=start,
            final_price=service.price,
            notes="Agendamento confirmado via ferramenta do agente.",
        )
        session.add(booking)
        session.commit()
        session.refresh(booking)
        return {"tool": request.tool, "status": "created", "appointment_id": booking.id, "preview": preview}

    if request.tool == "cancel":
        if not request.appointment_id:
            return {"tool": request.tool, "status": "missing_input", "message": "Informe o agendamento."}
        booking = session.get(Appointment, request.appointment_id)
        if not booking:
            return {"tool": request.tool, "status": "not_found"}
        if booking.status != AppointmentStatus.scheduled:
            return {"tool": request.tool, "status": "invalid_status"}
        if not request.confirm:
            return {"tool": request.tool, "status": "confirmation_required", "appointment_id": booking.id}
        booking.status = AppointmentStatus.canceled
        session.add(booking)
        session.commit()
        return {"tool": request.tool, "status": "canceled", "appointment_id": booking.id}

    return {"status": "unknown_tool"}
