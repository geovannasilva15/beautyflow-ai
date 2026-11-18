import os
import subprocess
import sys
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from app.db.database import normalize_database_url

BASE = "91b31bc719f6"


def run_alembic(url, *args, check=True):
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        env={**os.environ, "DATABASE_URL": url, "PYTHONIOENCODING": "utf-8"},
        check=check, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def test_database_urls_use_psycopg():
    assert normalize_database_url("postgres://a:b@host/db") == "postgresql+psycopg://a:b@host/db"
    assert normalize_database_url("postgresql://a:b@host/db") == "postgresql+psycopg://a:b@host/db"
    assert normalize_database_url("sqlite:///demo.db") == "sqlite:///demo.db"


@pytest.fixture(params=["sqlite", "postgresql"])
def migration_url(request, tmp_path):
    if request.param == "sqlite":
        yield f"sqlite:///{tmp_path / 'beautyflow.db'}"
        return
    postgres_url = os.getenv("TEST_POSTGRES_URL")
    if not postgres_url:
        pytest.skip("TEST_POSTGRES_URL must point at a disposable PostgreSQL database")
    root = create_engine(normalize_database_url(postgres_url))
    schema = "bf_test_" + uuid4().hex
    with root.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA {schema}"))
    url = make_url(normalize_database_url(postgres_url)).update_query_dict({
        "options": f"-csearch_path={schema}",
    })
    try:
        yield url.render_as_string(hide_password=False)
    finally:
        with root.begin() as conn:
            conn.execute(text(f"DROP SCHEMA {schema} CASCADE"))
        root.dispose()


def test_fresh_upgrade_matches_models(migration_url):
    run_alembic(migration_url, "upgrade", "head")
    run_alembic(migration_url, "check")
    engine = create_engine(migration_url)
    assert {"account", "loginsession", "whatsappmessage", "appointment", "alembic_version"} <= set(inspect(engine).get_table_names())
    engine.dispose()


def test_legacy_upgrade_backfills_duration_and_keeps_rows(migration_url):
    run_alembic(migration_url, "upgrade", BASE)
    engine = create_engine(migration_url)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO client (id, name, phone, created_at) VALUES (1, 'Cliente teste', '000', :now)"), {"now": now})
        conn.execute(text("""
            INSERT INTO service (id, name, category, description, duration_minutes, price, active, created_at)
            VALUES (1, 'Serviço teste', 'Pele', 'Exemplo', 45, 100, TRUE, :now)
        """), {"now": now})
        conn.execute(text("""
            INSERT INTO professional (id, name, specialty, active, created_at)
            VALUES (1, 'Profissional teste', 'Pele', TRUE, :now)
        """), {"now": now})
        conn.execute(text("""
            INSERT INTO appointment (id, client_id, service_id, professional_id, scheduled_at, final_price, status, created_at)
            VALUES (1, 1, 1, 1, :now, 100, 'scheduled', :now)
        """), {"now": now})
        conn.execute(text("DELETE FROM alembic_version"))

    # An unversioned populated database is stopped before baseline DDL.
    rejected = run_alembic(migration_url, "upgrade", "head", check=False)
    assert rejected.returncode != 0
    assert "base não está vazia" in rejected.stderr
    assert "account" not in inspect(engine).get_table_names()

    # This test created the legacy tables from BASE and knows their exact provenance.
    run_alembic(migration_url, "stamp", BASE)
    run_alembic(migration_url, "upgrade", "head")
    run_alembic(migration_url, "upgrade", "head")
    run_alembic(migration_url, "check")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT name FROM client")).scalar_one() == "Cliente teste"
        assert conn.execute(text("SELECT duration_minutes FROM appointment")).scalar_one() == 45
    engine.dispose()
