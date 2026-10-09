from __future__ import annotations

from datetime import date, datetime, time, timedelta
import re
import unicodedata

from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.time import (
    business_now,
    business_timezone,
    ensure_utc,
    local_datetime_to_utc,
    utc_now,
    utc_to_business,
)
from app.db.models import Appointment, AppointmentStatus, Client, Professional, Service

settings = get_settings()

SERVICE_KEYWORDS = {
    "sobrancelha": ["sobrancelha", "design", "brow"],
    "hidratacao": ["hidratacao", "cabelo", "fios", "frizz"],
    "limpeza de pele": ["limpeza de pele", "pele", "facial", "skincare"],
    "manicure": ["unha", "manicure", "esmaltacao"],
}


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", without_accents).strip()


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", _normalize_text(value)) if len(token) > 2}


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
    if not services:
        return None

    normalized_text = _normalize_text(text)
    text_tokens = _tokens(text)
    best_service: Service | None = None
    best_score = 0

    for service in services:
        searchable = _normalize_text(
            f"{service.name} {service.category} {service.description} {service.tags or ''}"
        )
        score = sum(1 for token in text_tokens if token in searchable)

        if _normalize_text(service.name) in normalized_text:
            score += 8
        if _normalize_text(service.category) in normalized_text:
            score += 4

        for canonical, keywords in SERVICE_KEYWORDS.items():
            if any(_normalize_text(keyword) in normalized_text for keyword in keywords):
                if canonical in searchable:
                    score += 5

        if score > best_score:
            best_score = score
            best_service = service

    return best_service if best_score > 0 else None


def find_professional_for_service(session: Session, service: Service) -> Professional | None:
    professionals = session.exec(
        select(Professional).where(Professional.active == True).order_by(Professional.name)  # noqa: E712
    ).all()
    if not professionals:
        return None

    service_tokens = _tokens(f"{service.name} {service.category} {service.tags or ''}")
    best_professional = professionals[0]
    best_score = -1

    for professional in professionals:
        specialty = _normalize_text(professional.specialty)
        score = sum(1 for token in service_tokens if token in specialty)

        for keyword in ["cabelo", "estetica", "facial", "sobrancelha", "unha"]:
            if keyword in _normalize_text(service.category) and keyword in specialty:
                score += 5

        if score > best_score:
            best_score = score
            best_professional = professional

    return best_professional


def parse_requested_datetime(text: str) -> datetime:
    now_local = business_now()
    normalized = _normalize_text(text)
    base_date = now_local.date() + timedelta(days=1)

    date_match = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", normalized)
    if date_match:
        day = int(date_match.group(1))
        month = int(date_match.group(2))
        year = int(date_match.group(3)) if date_match.group(3) else now_local.year
        if year < 100:
            year += 2000
        try:
            base_date = date(year, month, day)
        except ValueError:
            base_date = now_local.date() + timedelta(days=1)
    elif "amanha" in normalized:
        base_date = now_local.date() + timedelta(days=1)
    elif "hoje" in normalized:
        base_date = now_local.date()
    else:
        weekdays = {
            "segunda": 0,
            "terca": 1,
            "quarta": 2,
            "quinta": 3,
            "sexta": 4,
            "sabado": 5,
            "domingo": 6,
        }
        for label, weekday in weekdays.items():
            if label in normalized:
                days_ahead = (weekday - now_local.weekday()) % 7
                base_date = now_local.date() + timedelta(days=days_ahead or 7)
                break

    hour, minute = 14, 0
    time_match = re.search(r"\b([01]?\d|2[0-3])(?:h([0-5]\d)?|:([0-5]\d))\b", normalized)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or time_match.group(3) or 0)
    else:
        plain_hour = re.search(r"\bas\s+([01]?\d|2[0-3])\b", normalized)
        if plain_hour:
            hour = int(plain_hour.group(1))

    local_value = datetime.combine(base_date, time(hour, minute), tzinfo=business_timezone())
    return local_datetime_to_utc(local_value)


def _has_explicit_datetime_hint(text: str) -> bool:
    normalized = _normalize_text(text)
    return bool(
        any(word in normalized for word in ["hoje", "amanha", "segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"])
        or re.search(r"\b\d{1,2}[/-]\d{1,2}", normalized)
        or re.search(r"\b([01]?\d|2[0-3])(?:h|:)", normalized)
        or re.search(r"\bas\s+([01]?\d|2[0-3])\b", normalized)
    )


def _appointment_duration(session: Session, appointment: Appointment) -> int:
    service = session.get(Service, appointment.service_id)
    return service.duration_minutes if service else 60


def is_within_business_hours(scheduled_at: datetime, duration_minutes: int) -> bool:
    local_start = utc_to_business(scheduled_at)
    local_end = local_start + timedelta(minutes=duration_minutes)
    opening = datetime.combine(
        local_start.date(),
        time(settings.business_open_hour, 0),
        tzinfo=business_timezone(),
    )
    closing = datetime.combine(
        local_start.date(),
        time(settings.business_close_hour, 0),
        tzinfo=business_timezone(),
    )
    return opening <= local_start and local_end <= closing


def has_conflict(
    session: Session,
    professional_id: int,
    scheduled_at: datetime,
    duration_minutes: int,
    exclude_appointment_id: int | None = None,
) -> bool:
    requested_start = ensure_utc(scheduled_at)
    requested_end = requested_start + timedelta(minutes=duration_minutes)
    appointments = session.exec(
        select(Appointment).where(
            Appointment.professional_id == professional_id,
            Appointment.status == AppointmentStatus.scheduled,
        )
    ).all()

    for appointment in appointments:
        if exclude_appointment_id and appointment.id == exclude_appointment_id:
            continue
        existing_start = ensure_utc(appointment.scheduled_at)
        existing_end = existing_start + timedelta(minutes=_appointment_duration(session, appointment))
        if requested_start < existing_end and requested_end > existing_start:
            return True

    return False


def appointment_slot_error(
    session: Session,
    professional_id: int,
    service_id: int,
    scheduled_at: datetime,
    exclude_appointment_id: int | None = None,
) -> str | None:
    service = session.get(Service, service_id)
    professional = session.get(Professional, professional_id)
    if not service:
        return "Serviço não encontrado."
    if not professional or not professional.active:
        return "Profissional não encontrado ou inativo."

    scheduled_at = ensure_utc(scheduled_at)
    if scheduled_at <= utc_now():
        return "Escolha um horário futuro."

    if not is_within_business_hours(scheduled_at, service.duration_minutes):
        return (
            f"O atendimento precisa terminar dentro do horário de funcionamento "
            f"({settings.business_open_hour:02d}:00–{settings.business_close_hour:02d}:00)."
        )

    if has_conflict(
        session,
        professional_id,
        scheduled_at,
        service.duration_minutes,
        exclude_appointment_id=exclude_appointment_id,
    ):
        return "Esse horário conflita com outro atendimento do profissional."

    return None


def get_available_slots(
    session: Session,
    professional_id: int,
    service_id: int,
    target_date: date,
) -> list[datetime]:
    service = session.get(Service, service_id)
    professional = session.get(Professional, professional_id)
    if not service or not professional or not professional.active:
        return []

    local_now = business_now()
    cursor = datetime.combine(
        target_date,
        time(settings.business_open_hour, 0),
        tzinfo=business_timezone(),
    )
    closing = datetime.combine(
        target_date,
        time(settings.business_close_hour, 0),
        tzinfo=business_timezone(),
    )
    step = timedelta(minutes=max(settings.slot_interval_minutes, 15))
    duration = timedelta(minutes=service.duration_minutes)
    slots: list[datetime] = []

    while cursor + duration <= closing:
        slot_utc = local_datetime_to_utc(cursor)
        if cursor > local_now and not has_conflict(
            session,
            professional_id,
            slot_utc,
            service.duration_minutes,
        ):
            slots.append(cursor)
        cursor += step

    return slots


def find_next_available_slots(
    session: Session,
    professional_id: int,
    service_id: int,
    start_date: date | None = None,
    limit: int = 3,
    search_days: int = 14,
) -> list[datetime]:
    start = start_date or business_now().date()
    found: list[datetime] = []

    for offset in range(search_days):
        found.extend(get_available_slots(session, professional_id, service_id, start + timedelta(days=offset)))
        if len(found) >= limit:
            break

    return found[:limit]


def _format_slots(slots: list[datetime]) -> str:
    return ", ".join(slot.strftime("%d/%m às %H:%M") for slot in slots)


def _next_active_appointment(session: Session, client_id: int) -> Appointment | None:
    appointments = session.exec(
        select(Appointment).where(
            Appointment.client_id == client_id,
            Appointment.status == AppointmentStatus.scheduled,
        )
    ).all()
    upcoming = [appointment for appointment in appointments if ensure_utc(appointment.scheduled_at) >= utc_now()]
    if not upcoming:
        return None
    return min(upcoming, key=lambda appointment: ensure_utc(appointment.scheduled_at))


def create_appointment_from_message(
    session: Session,
    client_name: str,
    client_phone: str,
    message: str,
) -> tuple[str, int | None]:
    client = find_or_create_client(session, client_name, client_phone)
    service = find_service_from_text(session, message)
    if not service:
        return (
            "Posso agendar para você. Qual serviço deseja? Por exemplo: hidratação, limpeza de pele ou design de sobrancelhas.",
            None,
        )

    professional = find_professional_for_service(session, service)
    if not professional:
        return "Não encontrei profissional ativo para esse serviço no momento.", None

    scheduled_at = parse_requested_datetime(message)
    error = appointment_slot_error(session, professional.id, service.id, scheduled_at)
    if error:
        slots = find_next_available_slots(
            session,
            professional.id,
            service.id,
            start_date=utc_to_business(scheduled_at).date(),
        )
        suggestion = f" Tenho estas opções: {_format_slots(slots)}." if slots else ""
        return f"{error}{suggestion}", None

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

    local_time = utc_to_business(appointment.scheduled_at)
    response = (
        f"Perfeito, {client.name}! Seu horário para {service.name} foi agendado "
        f"para {local_time.strftime('%d/%m às %H:%M')} com {professional.name}. Te esperamos! 💎"
    )
    return response, appointment.id


def cancel_latest_appointment(session: Session, client_phone: str) -> tuple[str, int | None]:
    client = session.exec(select(Client).where(Client.phone == client_phone)).first()
    if not client:
        return "Não encontrei cadastro com esse telefone. Pode me informar seu nome e o horário que deseja cancelar?", None

    appointment = _next_active_appointment(session, client.id)
    if not appointment:
        return "Não encontrei agendamento futuro ativo para cancelar. Deseja que eu procure um novo horário?", None

    appointment.status = AppointmentStatus.canceled
    session.add(appointment)
    session.commit()
    session.refresh(appointment)

    return (
        "Seu próximo agendamento foi cancelado com sucesso. Se quiser, posso procurar outro horário para você.",
        appointment.id,
    )


def reschedule_latest_appointment(
    session: Session,
    client_phone: str,
    message: str,
) -> tuple[str, int | None, bool]:
    client = session.exec(select(Client).where(Client.phone == client_phone)).first()
    if not client:
        return "Não encontrei cadastro com esse telefone para reagendar.", None, False

    appointment = _next_active_appointment(session, client.id)
    if not appointment:
        return "Não encontrei agendamento futuro ativo para reagendar.", None, False

    service = session.get(Service, appointment.service_id)
    if not service:
        return "Não encontrei o serviço vinculado ao seu agendamento.", appointment.id, False

    if not _has_explicit_datetime_hint(message):
        slots = find_next_available_slots(
            session,
            appointment.professional_id,
            appointment.service_id,
            start_date=business_now().date(),
        )
        if slots:
            return (
                f"Claro! Para {service.name}, tenho estas opções: {_format_slots(slots)}. "
                "Envie a data e o horário desejados.",
                appointment.id,
                False,
            )
        return "Não encontrei horários livres nos próximos dias.", appointment.id, False

    requested_at = parse_requested_datetime(message)
    error = appointment_slot_error(
        session,
        appointment.professional_id,
        appointment.service_id,
        requested_at,
        exclude_appointment_id=appointment.id,
    )
    if error:
        slots = find_next_available_slots(
            session,
            appointment.professional_id,
            appointment.service_id,
            start_date=utc_to_business(requested_at).date(),
        )
        suggestion = f" Tenho estas opções: {_format_slots(slots)}." if slots else ""
        return f"{error}{suggestion}", appointment.id, False

    appointment.scheduled_at = requested_at
    appointment.status = AppointmentStatus.scheduled
    session.add(appointment)
    session.commit()
    session.refresh(appointment)

    local_time = utc_to_business(appointment.scheduled_at)
    return (
        f"Pronto! Seu atendimento de {service.name} foi reagendado para "
        f"{local_time.strftime('%d/%m às %H:%M')}.",
        appointment.id,
        True,
    )
