from __future__ import annotations

import hashlib

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from app.core.time import utc_now
from app.db.database import get_session
from app.db.models import Account, LoginSession

bearer = HTTPBearer(auto_error=False)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def session_account(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: Session = Depends(get_session),
) -> Account:
    if credentials and len(credentials.credentials) == 43:
        account = session.exec(
            select(Account)
            .join(LoginSession, LoginSession.account_id == Account.id)
            .where(
                LoginSession.token_hash == token_digest(credentials.credentials),
                LoginSession.expires_at > utc_now(),
                Account.active.is_(True),
            )
        ).first()
        if account:
            return account
    raise HTTPException(
        status_code=401, detail="Entre novamente para continuar.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def current_account(account: Account = Depends(session_account)) -> Account:
    if account.must_change_password:
        raise HTTPException(status_code=403, detail="Troque a senha inicial para acessar o painel.")
    return account


def require_admin(account: Account = Depends(current_account)) -> Account:
    if account.role != "admin":
        raise HTTPException(status_code=403, detail="Ação reservada à administração.")
    return account
