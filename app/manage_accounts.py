"""Operator-only bootstrap and password recovery on the API host."""
from __future__ import annotations

from argparse import ArgumentParser
from getpass import GetPassWarning, getpass
import warnings

from fastapi import HTTPException
from sqlalchemy import delete
from sqlmodel import Session, select

from app.api.auth import AccountCreate, add_account
from app.core.passwords import hash_password
from app.db.database import TransactionLock, engine, lock_transaction
from app.db.models import Account, LoginSession


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["bootstrap", "reset-password"])
    args = parser.parse_args()
    email = input("E-mail: ").strip().lower()
    name = input("Nome: ") if args.action == "bootstrap" else None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", GetPassWarning)
            password = getpass("Nova senha (16 a 128 caracteres): ")
            repeat = getpass("Repita a senha: ")
    except GetPassWarning:
        parser.exit(1, "Abra um terminal interativo para digitar a senha sem exibi-la.\n")
    if password != repeat:
        parser.exit(1, "As senhas não coincidem.\n")

    try:
        with Session(engine) as session:
            lock_transaction(session, TransactionLock.ACCOUNT)
            if args.action == "bootstrap":
                if session.exec(select(Account.id).limit(1)).first() is not None:
                    parser.exit(1, "A instalação já possui contas.\n")
                add_account(session, AccountCreate(email=email, name=name, password=password, role="admin"))
            else:
                account = session.exec(select(Account).where(Account.email == email, Account.active.is_(True))).first()
                if not account:
                    parser.exit(1, "Conta ativa não localizada.\n")
                account.password_hash = hash_password(password)
                account.must_change_password = True
                session.execute(delete(LoginSession).where(LoginSession.account_id == account.id))
                session.commit()
    except (ValueError, HTTPException):
        parser.exit(1, "Verifique o e-mail, o nome e os requisitos da senha.\n")
    print("Conta atualizada.")


if __name__ == "__main__":
    main()
