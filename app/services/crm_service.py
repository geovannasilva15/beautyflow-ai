from __future__ import annotations

from datetime import timedelta
from sqlmodel import Session, select
from app.core.time import ensure_utc, utc_now
from app.db.models import Appointment, AppointmentStatus, Client, Service


def get_crm_metrics(session: Session, inactive_days: int = 60) -> dict:
    clients = session.exec(select(Client)).all()
    appointments = session.exec(select(Appointment)).all()
    services = {service.id: service for service in session.exec(select(Service)).all()}
    today = utc_now()
    customers = []
    for client in clients:
        history = [a for a in appointments if a.client_id == client.id]
        completed = sorted(
            [a for a in history if a.status == AppointmentStatus.completed],
            key=lambda a: ensure_utc(a.scheduled_at),
            reverse=True,
        )
        last = ensure_utc(completed[0].scheduled_at) if completed else None
        frequencies = {}
        for appointment in completed:
            service = services.get(appointment.service_id)
            if service:
                frequencies[service.name] = frequencies.get(service.name, 0) + 1
        customers.append({
            "client_id": client.id,
            "client_name": client.name,
            "completed_visits": len(completed),
            "total_appointments": len(history),
            "total_spent": round(sum(a.final_price for a in completed), 2),
            "last_visit": last.isoformat() if last else None,
            "favorite_service": max(frequencies, key=frequencies.get) if frequencies else None,
            "inactive": bool(last and today - last > timedelta(days=inactive_days)),
        })
    return {
        "total_clients": len(clients),
        "returning_clients": sum(c["completed_visits"] >= 2 for c in customers),
        "inactive_clients": sum(c["inactive"] for c in customers),
        "customers": customers,
    }
