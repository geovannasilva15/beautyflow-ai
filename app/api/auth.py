from __future__ import annotations

import re
import secrets
from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.api_access import bearer, require_admin, session_account, token_digest
from app.core.passwords import hash_password, verify_password
from app.core.time import ensure_utc, utc_now
from app.db.database import TransactionLock, get_session, lock_transaction
from app.db.models import Account, LoginLimit, LoginSession

router = APIRouter(prefix="/auth", tags=["contas"])
DUMMY_HASH = "scrypt$32768$8$3$" + "00" * 16 + "$" + "00" * 32
SESSION_TTL = timedelta(hours=8)


class LoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


class AccountCreate(LoginRequest):
    name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=16, max_length=128)
    role: Literal["admin", "professional"] = "professional"

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+", value):
            raise ValueError("Informe um e-mail válido.")
        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if len(value.strip()) < 2:
            raise ValueError("Informe um nome.")
        return value.strip()


class AccountView(BaseModel):
    id: int
    email: str
    name: str
    role: str
    active: bool
    must_change_password: bool


class LoginResponse(BaseModel):
    access_token: str
    account: AccountView


class PasswordChange(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(min_length=16, max_length=128)


def add_account(session: Session, payload: AccountCreate, *, must_change_password: bool = False) -> Account:
    account = Account(
        **payload.model_dump(exclude={"password"}), password_hash=hash_password(payload.password),
        must_change_password=must_change_password,
    )
    session.add(account)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="Já existe uma conta com esse e-mail.") from exc
    session.refresh(account)
    return account


def enforce_login_limit(session: Session, email: str) -> None:
    now = utc_now()
    lock_transaction(session, TransactionLock.LOGIN_LIMIT)
    session.execute(delete(LoginLimit).where(LoginLimit.expires_at <= now))
    limit = session.get(LoginLimit, token_digest(email))
    global_limit = session.get(LoginLimit, "global")
    for entry, maximum in ((limit, 8), (global_limit, 45)):
        if entry and entry.attempts >= maximum:
            remaining = max(1, int((ensure_utc(entry.expires_at) - now).total_seconds()))
            raise HTTPException(
                status_code=429, detail="Muitas tentativas. Tente novamente mais tarde.",
                headers={"Retry-After": str(remaining)},
            )
    for entry, key, window in (
        (limit, token_digest(email), timedelta(minutes=15)),
        (global_limit, "global", timedelta(minutes=1)),
    ):
        entry = entry or LoginLimit(key=key, expires_at=now + window)
        entry.attempts += 1
        session.add(entry)
    session.commit()


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, response: Response, session: Session = Depends(get_session)) -> dict:
    response.headers["Cache-Control"] = "no-store"
    email = payload.email.strip().lower()
    enforce_login_limit(session, email)
    account = session.exec(select(Account).where(Account.email == email)).first()
    stored_hash = account.password_hash if account else DUMMY_HASH
    if not verify_password(payload.password, stored_hash) or not account or not account.active:
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")

    # Lock and recheck the account after hashing in case its password changed concurrently.
    account_id = account.id
    session.rollback()
    lock_transaction(session, TransactionLock.ACCOUNT)
    account = session.get(Account, account_id)
    if not account or not account.active or account.password_hash != stored_hash:
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")
    token = secrets.token_urlsafe(32)
    session.execute(delete(LoginLimit).where(LoginLimit.key == token_digest(email)))
    session.execute(delete(LoginSession).where(LoginSession.expires_at <= utc_now()))
    session.add(LoginSession(
        token_hash=token_digest(token), account_id=account.id, expires_at=utc_now() + SESSION_TTL,
    ))
    session.commit()
    return {"access_token": token, "account": account}


@router.get("/me", response_model=AccountView)
def me(account: Account = Depends(session_account)) -> Account:
    return account


@router.post("/logout", status_code=204)
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: Session = Depends(get_session),
) -> None:
    if credentials and len(credentials.credentials) == 43:
        session.execute(delete(LoginSession).where(LoginSession.token_hash == token_digest(credentials.credentials)))
        session.commit()


@router.post("/password", status_code=204)
def change_password(
    payload: PasswordChange,
    account: Account = Depends(session_account),
    session: Session = Depends(get_session),
) -> None:
    # Roll back the read transaction before taking the SQLite write lock.
    account_id = account.id
    session.rollback()
    lock_transaction(session, TransactionLock.ACCOUNT)
    account = session.get(Account, account_id)
    if not account or not account.active or not verify_password(payload.current_password, account.password_hash):
        raise HTTPException(status_code=401, detail="Senha atual incorreta.")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=422, detail="Escolha uma senha diferente da atual.")
    account.password_hash = hash_password(payload.new_password)
    account.must_change_password = False
    session.execute(delete(LoginSession).where(LoginSession.account_id == account_id))
    session.commit()


@router.post("/accounts", response_model=AccountView, status_code=201)
def create_account(
    payload: AccountCreate,
    session: Session = Depends(get_session),
    _: Account = Depends(require_admin),
) -> Account:
    return add_account(session, payload, must_change_password=True)


@router.get("/accounts", response_model=list[AccountView])
def list_accounts(session: Session = Depends(get_session), _: Account = Depends(require_admin)) -> list[Account]:
    return session.exec(select(Account).order_by(Account.name)).all()


@router.delete("/accounts/{account_id}", status_code=204)
def disable_account(
    account_id: int,
    admin: Account = Depends(require_admin),
    session: Session = Depends(get_session),
) -> None:
    admin_id = admin.id
    session.rollback()
    lock_transaction(session, TransactionLock.ACCOUNT)
    actor = session.get(Account, admin_id)
    if not actor or not actor.active:
        raise HTTPException(status_code=403, detail="Conta desativada.")
    account = session.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")
    if account.id == admin_id:
        raise HTTPException(status_code=409, detail="Sua própria conta não pode ser desativada.")
    account.active = False
    session.execute(delete(LoginSession).where(LoginSession.account_id == account_id))
    session.commit()
