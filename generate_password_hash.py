"""Run locally and paste the resulting hash into server secrets, never Git."""
from getpass import getpass

from app.core.passwords import hash_password

if __name__ == "__main__":
    password = getpass("Nova senha (mínimo de 16 caracteres): ")
    if password != getpass("Confirme a senha: "):
        raise SystemExit("As senhas não coincidem.")
    try:
        print(hash_password(password))
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
