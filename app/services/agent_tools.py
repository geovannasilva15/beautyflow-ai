from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import json
import secrets
from typing import Literal

from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.core.time import ensure_utc, local_datetime_to_utc, utc_now, utc_to_business
from app.db.models import AgentConfirmation, Appointment, AppointmentStatus, Client, Professional, Service
from app.services.appointment_service import appointment_slot_error, get_available_slots


class AgentToolRequest(BaseModel):
    tool: Literal["list_services", "find_client", "availability", "book", "cancel", "reschedule"]
    client_id: int | None = None
    service_id: int | None = None
    professional_id: int | None = None
    appointment_id: int | None = None
    scheduled_at: datetime | None = None
    query: str | None = Field(default=None, max_length=120)
    confirm: bool = False
    confirmation_token: str | None = Field(default=None, max_length=200)


def _confirmation(
    session: Session, request: AgentToolRequest, actor_id: int, preview: dict,
) -> dict | None:
    args = request.model_dump(mode="json", exclude={"confirm", "confirmation_token"}, exclude_none=True)
    if request.scheduled_at:
        args["scheduled_at"] = local_datetime_to_utc(request.scheduled_at).isoformat()
    digest = hashlib.sha256(json.dumps([actor_id, args, preview], sort_keys=True).encode()).hexdigest()
    if not request.confirm:
        token = secrets.token_urlsafe(32)
        session.add(AgentConfirmation(
            token_hash=hashlib.sha256(token.encode()).hexdigest(), action_hash=digest,
            expires_at=utc_now() + timedelta(minutes=10),
        ))
        session.commit()
        return {
            "tool": request.tool, "status": "confirmation_required", "preview": preview,
            "appointment_id": request.appointment_id, "confirmation_token": token, "expires_in_seconds": 600,
        }

    token_hash = hashlib.sha256((request.confirmation_token or "").encode()).hexdigest()
    confirmation = session.exec(
        select(AgentConfirmation).where(AgentConfirmation.token_hash == token_hash)
    ).first()
    if (not confirmation or confirmation.consumed or confirmation.action_hash != digest
            or ensure_utc(confirmation.expires_at) <= utc_now()):
        return {"tool": request.tool, "status": "invalid_confirmation"}
    confirmation.consumed = True
    return None


def execute_agent_tool(session: Session, request: AgentToolRequest, actor_id: int) -> dict:
    """Run system queries directly and require a matching preview for every assisted mutation."""
    result = {"tool": request.tool}
    if request.tool == "list_services":
        services = session.exec(select(Service).where(Service.active.is_(True)).order_by(Service.name)).all()
        return {**result, "status": "ok", "data": [
            {"id": s.id, "name": s.name, "price": s.price, "duration_minutes": s.duration_minutes}
            for s in services
        ]}

    if request.tool == "find_client":
        if not request.query or not request.query.strip():
            return {**result, "status": "missing_input", "message": "Informe o nome da cliente."}
        clients = session.exec(select(Client).order_by(Client.name)).all()
        matches = [c for c in clients if request.query.strip().casefold() in c.name.casefold()]
        return {**result, "status": "ok", "data": [{"id": c.id, "name": c.name} for c in matches[:10]]}

    if request.tool == "availability":
        if not all([request.professional_id, request.service_id, request.scheduled_at]):
            return {**result, "status": "missing_input", "message": "Informe serviço, profissional e data."}
        professional = session.get(Professional, request.professional_id)
        service = session.get(Service, request.service_id)
        if not professional or not professional.active or not service or not service.active:
            return {**result, "status": "not_found"}
        target = utc_to_business(local_datetime_to_utc(request.scheduled_at)).date()
        slots = get_available_slots(session, professional.id, service.id, target)
        return {**result, "status": "ok", "slots": [s.isoformat() for s in slots]}

    booking = None
    if request.tool == "book":
        if not all([request.client_id, request.service_id, request.professional_id, request.scheduled_at]):
            return {**result, "status": "missing_input", "message": "Informe cliente, serviço, profissional e horário."}
        client = session.get(Client, request.client_id)
        service = session.get(Service, request.service_id)
        professional = session.get(Professional, request.professional_id)
        if not client or not service or not service.active or not professional or not professional.active:
            return {**result, "status": "not_found"}
        start = local_datetime_to_utc(request.scheduled_at)
        booking = Appointment(
            client_id=client.id, service_id=service.id, professional_id=professional.id,
            scheduled_at=start, final_price=service.price, duration_minutes=service.duration_minutes,
            notes="Agendamento confirmado via ferramenta do assistente.",
        )
    else:
        if not request.appointment_id or (request.tool == "reschedule" and not request.scheduled_at):
            return {**result, "status": "missing_input", "message": "Informe o agendamento e, ao reagendar, o novo horário."}
        booking = session.get(Appointment, request.appointment_id)
        if not booking:
            return {**result, "status": "not_found"}
        if booking.status != AppointmentStatus.scheduled:
            return {**result, "status": "invalid_status"}
        client = session.get(Client, booking.client_id)
        service = session.get(Service, booking.service_id)
        professional = session.get(Professional, booking.professional_id)
        if not client or not service or not professional:
            return {**result, "status": "not_found"}
        start = local_datetime_to_utc(request.scheduled_at) if request.tool == "reschedule" else booking.scheduled_at

    if request.tool != "cancel":
        error = appointment_slot_error(
            session, professional.id, service.id, start, exclude_appointment_id=booking.id,
            duration_minutes=booking.duration_minutes,
        )
        if error:
            return {**result, "status": "unavailable", "message": error}

    preview = {
        "client": client.name, "service": service.name, "professional": professional.name,
        "scheduled_at": utc_to_business(start).isoformat(), "price": booking.final_price,
        "duration_minutes": booking.duration_minutes or service.duration_minutes,
    }
    if request.tool == "reschedule":
        preview["previous_at"] = utc_to_business(booking.scheduled_at).isoformat()
    pending = _confirmation(session, request, actor_id, preview)
    if pending:
        return pending

    if request.tool == "cancel":
        booking.status = AppointmentStatus.canceled
    else:
        booking.scheduled_at = start
    session.add(booking)
    session.commit()
    session.refresh(booking)
    labels = {"book": "created", "cancel": "canceled", "reschedule": "rescheduled"}
    return {**result, "status": labels[request.tool], "appointment_id": booking.id, "preview": preview}
