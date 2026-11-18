from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from app.core.passwords import hash_password
from app.db.database import get_session
from app.db.models import Account
from app.main import app

TEST_PASSWORD = "senha inicial fictícia para testes"


@pytest.fixture(scope="session")
def test_password_hash() -> str:
    return hash_password(TEST_PASSWORD)


@pytest.fixture
def anonymous(tmp_path, monkeypatch, test_password_hash) -> Generator[TestClient, None, None]:
    test_engine = create_engine(f"sqlite:///{tmp_path / 'api.db'}", connect_args={"check_same_thread": False})

    @event.listens_for(test_engine, "connect")
    def enable_foreign_keys(dbapi_connection, _):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        session.add(Account(
            email="admin@example.test", name="Admin Teste", role="admin", password_hash=test_password_hash,
        ))
        session.commit()

    def get_test_session() -> Generator[Session, None, None]:
        with Session(test_engine) as session:
            yield session

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_DEMO_SIMULATION", "true")
    app.dependency_overrides[get_session] = get_test_session
    try:
        with TestClient(app) as api:
            yield api
    finally:
        app.dependency_overrides.clear()
        test_engine.dispose()


@pytest.fixture
def client(anonymous: TestClient) -> TestClient:
    result = anonymous.post("/api/auth/login", json={"email": "admin@example.test", "password": TEST_PASSWORD})
    assert result.status_code == 200, result.text
    anonymous.headers["Authorization"] = "Bearer " + result.json()["access_token"]
    return anonymous
