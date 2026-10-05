from __future__ import annotations

from datetime import datetime, timedelta, time, timezone
import re

from sqlmodel import Session, select

from app.db.models import Appointment, AppointmentStatus, Client, Professional, Service


SERVICE_KEYWORDS = {
    "sobrancelha": ["sobrancelha", "design", "brow"],
    "hidratação": ["hidratação", "hidratacao", "cabelo", "fios"],
    "limpeza de pele": ["limpeza de pele", "pele", "facial"],
    "manicure": ["unha", "manicure", "esmaltação", "esmaltacao"],
}


def find_or_create_client(session: Session, name: str, phone: str) -> Client:
    client = session.exec(select(Client).where(Client.phone == phone)).first()
    if client:
        return client
    client = Client(name=name, phone=phone, interests="Atendimento via WhatsApp")
    session.add(client)
    session.commit()
    session.refresh(client)
    return client


def find_service_from_text(session: Session, text: str) -> Service | None:
    services = session.exec(select(Service).where(Service.active == True)).all()  # noqa: E712
    text_lower = text.lower()
    for service in services:
        searchable = f"{service.name} {service.category} {service.tags or ''}".lower()
        if any(word in searchable or word in text_lower for word in text_lower.split()):
            for token in [service.name.lower(), service.category.lower()]:
                if token and token in text_lower:
                    return service
    for canonical, keywords in SERVICE_KEYWORDS.items():
        if any(keyword in text_lower for keyword in keywords):
            for service in services:
                if canonical in f"{service.name} {service.tags or ''}".lower():
                    return service
    return services[0] if services else None


def first_active_professional(session: Session) -> Professional | None:
    return session.exec(select(Professional).where(Professional.active == True)).first()  # noqa: E712


def parse_requested_datetime(text: str) -> datetime:
    now = datetime.now(timezone.utc)
    text_lower = text.lower()

    if "amanhã" in text_lower or "amanha" in text_lower:
        base_date = now.date() + timedelta(days=1)
    elif "hoje" in text_lower:
        base_date = now.date()
    elif "sexta" in text_lower:
        days_ahead = (4 - now.weekday()) % 7 or 7
        base_date = now.date() + timedelta(days=days_ahead)
    elif "sábado" in text_lower or "sabado" in text_lower:
        days_ahead = (5 - now.weekday()) % 7 or 7
        base_date = now.date() + timedelta(days=days_ahead)
    else:
        base_date = now.date() + timedelta(days=1)

    match = re.search(r"(\d{1,2})(?:h|:)(\d{0,2})", text_lower)
    if match:
        hour = min(int(match.group(1)), 23)
        minute = int(match.group(2) or 0)
    else:
        hour, minute = 14, 0

    return datetime.combine(base_date, time(hour, minute), tzinfo=timezone.utc)


def has_conflict(session: Session, professional_id: int, scheduled_at: datetime) -> bool:
    start = scheduled_at - timedelta(minutes=30)
    end = scheduled_at + timedelta(minutes=30)
    return session.exec(
        select(Appointment).where(
            Appointment.professional_id == professional_id,
            Appointment.status == AppointmentStatus.scheduled,
            Appointment.scheduled_at >= start,
            Appointment.scheduled_at <= end,
        )
    ).first() is not None


def create_appointment_from_message(session: Session, client_name: str, client_phone: str, message: str) -> tuple[str, int | None]:
    client = find_or_create_client(session, client_name, client_phone)
    service = find_service_from_text(session, message)
    professional = first_active_professional(session)

    if not service or not professional:
        return "Não encontrei serviço ou profissional disponível no momento. Cadastre serviços e profissionais primeiro.", None

    scheduled_at = parse_requested_datetime(message)
    if has_conflict(session, professional.id, scheduled_at):
        suggestion = scheduled_at + timedelta(hours=1)
        return (
            f"Esse horário está ocupado. Tenho uma opção em {suggestion.strftime('%d/%m às %H:%M')}. Deseja reservar?",
            None,
        )

    appointment = Appointment(
        client_id=client.id,
        service_id=service.id,
        professional_id=professional.id,
        scheduled_at=scheduled_at,
        final_price=service.price,
        notes="Criado pelo agente simulado de WhatsApp.",
    )
    session.add(appointment)
    session.commit()
    session.refresh(appointment)

    response = (
        f"Perfeito, {client.name}! Seu horário para {service.name} foi agendado "
        f"para {scheduled_at.strftime('%d/%m às %H:%M')}. Te esperamos! 💎"
    )
    return response, appointment.id


def cancel_latest_appointment(session: Session, client_phone: str) -> tuple[str, int | None]:
    client = session.exec(select(Client).where(Client.phone == client_phone)).first()
    if not client:
        return "Não encontrei cadastro com esse telefone. Pode me informar seu nome e o horário que deseja cancelar?", None

    appointment = session.exec(
        select(Appointment)
        .where(Appointment.client_id == client.id, Appointment.status == AppointmentStatus.scheduled)
        .order_by(Appointment.scheduled_at.desc())
    ).first()

    if not appointment:
        return "Não encontrei agendamento ativo para cancelar. Deseja que eu procure um novo horário para você?", None

    appointment.status = AppointmentStatus.canceled
    session.add(appointment)
    session.commit()
    session.refresh(appointment)

    return (
        "Seu agendamento foi cancelado com sucesso. Deseja que eu procure outro horário disponível para reagendar?",
        appointment.id,
    )
