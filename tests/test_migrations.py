import os
import subprocess
import sys

from sqlalchemy import create_engine, inspect, text

from app.db.database import normalize_database_url


def test_database_urls_use_psycopg():
    assert normalize_database_url("postgres://a:b@host/db") == "postgresql+psycopg://a:b@host/db"
    assert normalize_database_url("postgresql://a:b@host/db") == "postgresql+psycopg://a:b@host/db"
    assert normalize_database_url("sqlite:///demo.db") == "sqlite:///demo.db"


def test_migration_creates_schema_and_repeat_preserves_data(tmp_path):
    url = f"sqlite:///{tmp_path / 'beautyflow.db'}"
    env = {**os.environ, "DATABASE_URL": url}

    def upgrade():
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], env=env, check=True, capture_output=True)

    upgrade()
    engine = create_engine(url)
    assert {"client", "appointment", "alembic_version"} <= set(inspect(engine).get_table_names())
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO client (name, phone, created_at) VALUES ('Cliente teste', '000', '2026-01-01 00:00:00')"))
    upgrade()
    with engine.connect() as conn:
        assert conn.execute(text("SELECT name FROM client")).scalar_one() == "Cliente teste"
    engine.dispose()
