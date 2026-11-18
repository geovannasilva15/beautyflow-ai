from datetime import timedelta

import pytest
from sqlmodel import select

from app.core.passwords import hash_password, verify_password
from app.core.time import utc_now
from app.db.database import get_session
from app.db.models import LoginSession
from app.main import app
from tests.conftest import TEST_PASSWORD


def test_password_hash_is_salted_and_rejects_invalid_values():
    first = hash_password(TEST_PASSWORD)
    assert first != hash_password(TEST_PASSWORD)
    assert verify_password(TEST_PASSWORD, first)
    assert not verify_password("outra senha", first)
    assert not verify_password(TEST_PASSWORD, "invalid")
    with pytest.raises(ValueError):
        hash_password("curta")


def test_public_surface_has_no_demo_or_shared_access(anonymous):
    assert anonymous.get("/healthz").status_code == 200
    for path in ("clients", "services", "professionals", "appointments", "dashboard", "auth/accounts", "whatsapp/inbox"):
        assert anonymous.get(f"/api/{path}", headers={"X-API-Key": "old-preview"}).status_code == 401
    invalid = anonymous.post("/api/auth/login", json={"email": "geovanna@beautyflow.ai", "password": "123456"})
    assert invalid.status_code == 401
    long_password = "sample-secret-" * 25
    invalid = anonymous.post("/api/auth/login", json={"email": "admin@example.test", "password": long_password})
    assert invalid.status_code == 422
    assert long_password not in invalid.text


def test_login_limit_and_generic_failures(anonymous):
    present = {"email": "admin@example.test", "password": "wrong"}
    absent = {**present, "email": "other@example.test"}
    assert anonymous.post("/api/auth/login", json=present).json() == anonymous.post("/api/auth/login", json=absent).json()
    for _ in range(7):
        assert anonymous.post("/api/auth/login", json=present).status_code == 401
    locked = anonymous.post("/api/auth/login", json={**present, "password": TEST_PASSWORD})
    assert locked.status_code == 429
    assert int(locked.headers["Retry-After"]) > 0


def test_individual_roles_account_revocation_and_logout(client):
    payload = {"name": "Profissional Teste", "role": "professional", "email": "p@example.test", "password": TEST_PASSWORD}
    created = client.post("/api/auth/accounts", json=payload)
    assert created.status_code == 201
    assert {"password", "password_hash"}.isdisjoint(created.json())
    assert created.json()["must_change_password"]
    assert client.post("/api/auth/accounts", json=payload).status_code == 409
    session = client.post("/api/auth/login", json=payload)
    assert session.headers["Cache-Control"] == "no-store"
    headers = {"Authorization": "Bearer " + session.json()["access_token"]}
    assert client.get("/api/auth/me", headers=headers).json()["id"] == created.json()["id"]
    assert client.get("/api/dashboard", headers=headers).status_code == 403
    new_password = "senha pessoal da profissional"
    assert client.post("/api/auth/password", json={
        "current_password": TEST_PASSWORD, "new_password": new_password,
    }, headers=headers).status_code == 204
    assert client.get("/api/auth/me", headers=headers).status_code == 401
    payload["password"] = new_password
    session = client.post("/api/auth/login", json=payload)
    headers = {"Authorization": "Bearer " + session.json()["access_token"]}
    customer = client.post("/api/clients", json={"name": "Teste", "phone": "11900000000"}, headers=headers)
    assert customer.status_code == 200
    assert client.get("/api/clients", headers=headers).status_code == 200
    assert client.delete(f"/api/clients/{customer.json()['id']}", headers=headers).status_code == 403
    assert client.get("/api/auth/accounts", headers=headers).status_code == 403
    assert client.post("/api/auth/accounts", json=payload, headers=headers).status_code == 403
    assert client.post("/api/professionals", json={"name": "Nova", "specialty": "Pele"}, headers=headers).status_code == 403
    assert client.get("/api/whatsapp/inbox", headers=headers).status_code == 403
    assert client.delete(f"/api/auth/accounts/{created.json()['id']}").status_code == 204
    assert client.get("/api/auth/me", headers=headers).status_code == 401
    assert client.post("/api/auth/login", json=payload).status_code == 401
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/dashboard").status_code == 401


def test_expired_sessions_and_password_change(client):
    sessions = app.dependency_overrides[get_session]()
    db = next(sessions)
    try:
        token = db.exec(select(LoginSession)).one()
        assert token.token_hash != client.headers["Authorization"].split()[-1]
        token.expires_at = utc_now() - timedelta(seconds=1)
        db.commit()
    finally:
        sessions.close()

    assert client.get("/api/auth/me").status_code == 401
    valid = client.post("/api/auth/login", json={"email": "admin@example.test", "password": TEST_PASSWORD})
    headers = {"Authorization": "Bearer " + valid.json()["access_token"]}
    new_password = "exemplo de senha atualizada"
    assert client.post("/api/auth/password", json={
        "current_password": TEST_PASSWORD, "new_password": new_password,
    }, headers=headers).status_code == 204
    assert client.get("/api/auth/me", headers=headers).status_code == 401
    assert client.post("/api/auth/login", json={"email": "admin@example.test", "password": new_password}).status_code == 200


def test_first_admin_bootstrap_and_operator_recovery(tmp_path, monkeypatch):
    from sqlmodel import Session, SQLModel, create_engine

    from app import manage_accounts
    from app.db.models import Account

    engine = create_engine(f"sqlite:///{tmp_path / 'bootstrap.db'}")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(manage_accounts, "engine", engine)
    monkeypatch.setattr(manage_accounts, "getpass", lambda _: TEST_PASSWORD)

    def run(action, *inputs):
        answers = iter(inputs)
        monkeypatch.setattr("builtins.input", lambda _: next(answers))
        monkeypatch.setattr("sys.argv", ["manage_accounts", action])
        manage_accounts.main()

    run("bootstrap", "admin@example.test", "Gestora Exemplo")
    with pytest.raises(SystemExit) as result:
        run("bootstrap", "second@example.test", "Outra Pessoa")
    assert result.value.code == 1

    with Session(engine) as db:
        admin = db.exec(select(Account)).one()
        assert admin.role == "admin" and not admin.must_change_password
        assert verify_password(TEST_PASSWORD, admin.password_hash)
        account_id = admin.id
        db.add(LoginSession(token_hash="0" * 64, account_id=account_id, expires_at=utc_now() + timedelta(hours=1)))
        db.commit()

    recovery_password = "senha temporária de recuperação"
    monkeypatch.setattr(manage_accounts, "getpass", lambda _: recovery_password)
    run("reset-password", "admin@example.test")
    with Session(engine) as db:
        assert not db.exec(select(LoginSession)).all()
        admin = db.get(Account, account_id)
        assert admin.must_change_password and verify_password(recovery_password, admin.password_hash)
    engine.dispose()
