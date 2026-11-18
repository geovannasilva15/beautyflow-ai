import pytest

from app.core.passwords import hash_password, verify_password
from frontend.auth import credentials_valid


def test_password_hash_is_salted_and_rejects_invalid_values():
    password = "uma senha longa para teste"
    first = hash_password(password)
    assert first != hash_password(password)
    assert verify_password(password, first)
    assert not verify_password("outra senha", first)
    assert not verify_password(password, "invalid")
    with pytest.raises(ValueError):
        hash_password("curta")


def test_production_refuses_demo_and_requires_configured_credentials(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("APP_LOGIN_EMAIL", raising=False)
    monkeypatch.delenv("APP_LOGIN_PASSWORD_HASH", raising=False)
    assert not credentials_valid("geovanna@beautyflow.ai", "123456")
    monkeypatch.setenv("APP_LOGIN_EMAIL", "ADMIN@example.com")
    monkeypatch.setenv("APP_LOGIN_PASSWORD_HASH", hash_password("uma senha longa para teste"))
    assert credentials_valid("admin@example.com", "uma senha longa para teste")
    assert not credentials_valid("admin@example.com", "senha incorreta")
    assert not credentials_valid("outra@example.com", "uma senha longa para teste")


def test_demo_only_in_development(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    assert credentials_valid("geovanna@beautyflow.ai", "123456")
