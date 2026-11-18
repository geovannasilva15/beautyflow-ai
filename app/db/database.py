from __future__ import annotations

from collections.abc import Generator
from enum import IntEnum

from sqlalchemy import event, text
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings


def normalize_database_url(url: str) -> str:
    if url.startswith(("postgres://", "postgresql://")):
        return "postgresql+psycopg://" + url.split("://", 1)[1]
    return url


database_url = normalize_database_url(get_settings().database_url)
connect_args = (
    {"check_same_thread": False} if database_url.startswith("sqlite")
    else {"options": "-c timezone=UTC"}
)
engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True, hide_parameters=True)

if database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")


def create_db_and_tables() -> None:
    from app.db import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


class TransactionLock(IntEnum):
    LOGIN_LIMIT = 301
    ACCOUNT = 302
    SCHEDULE = 303
    WHATSAPP = 304


def lock_transaction(session: Session, key: TransactionLock) -> None:
    """Serialize competing updates across API processes until commit or rollback."""
    if session.get_bind().dialect.name == "postgresql":
        session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": int(key)})
    else:
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
