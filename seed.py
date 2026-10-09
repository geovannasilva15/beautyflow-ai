from __future__ import annotations

from datetime import datetime, time, timedelta

from sqlmodel import Session, select

from app.core.time import business_now, local_datetime_to_utc
from app.db.database import create_db_and_tables, engine
from app.db.models import Appointment, Campaign, Client, Professional, Service
from data.sample_data import SAMPLE_CLIENTS, SAMPLE_PROFESSIONALS, SAMPLE_SERVICES


def _future_local_slot(days: int, hour: int) -> datetime:
    target_date = business_now().date() + timedelta(days=days)
    return local_datetime_to_utc(datetime.combine(target_date, time(hour, 0)))


def seed() -> None:
    create_db_and_tables()

    with Session(engine) as session:
        if not session.exec(select(Client)).first():
            for item in SAMPLE_CLIENTS:
                session.add(Client(**item))
            session.commit()

        if not session.exec(select(Service)).first():
            for item in SAMPLE_SERVICES:
                session.add(Service(**item))
            session.commit()

        if not session.exec(select(Professional)).first():
            for item in SAMPLE_PROFESSIONALS:
                session.add(Professional(**item))
            session.commit()

        clients = session.exec(select(Client)).all()
        services = session.exec(select(Service)).all()
        professionals = session.exec(select(Professional)).all()

        if clients and services and professionals and not session.exec(select(Appointment)).first():
            session.add(
                Appointment(
                    client_id=clients[0].id,
                    service_id=services[0].id,
                    professional_id=professionals[0].id,
                    scheduled_at=_future_local_slot(1, 14),
                    final_price=services[0].price,
                    notes="Agendamento demo criado pelo seed.",
                )
            )
            session.add(
                Appointment(
                    client_id=clients[-1].id,
                    service_id=services[-1].id,
                    professional_id=professionals[-1].id,
                    scheduled_at=_future_local_slot(2, 16),
                    final_price=services[-1].price,
                    notes="Retorno para acompanhamento facial.",
                )
            )
            session.commit()

        if not session.exec(select(Campaign)).first():
            session.add(
                Campaign(
                    title="Promoção de hidratação",
                    message="Oi, tudo bem? Essa semana temos uma condição especial para hidratação profunda. Quer reservar um horário?",
                    target_audience="cabelo",
                    scheduled_at=_future_local_slot(1, 10),
                    status="scheduled",
                )
            )
            session.commit()

    print("BeautyFlow AI: dados iniciais criados com sucesso.")


if __name__ == "__main__":
    seed()
