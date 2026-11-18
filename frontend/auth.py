from __future__ import annotations

import hmac
import os

import streamlit as st

from app.core.passwords import verify_password
from frontend.styles import apply_login_styles

DEMO_USERS = {
    "geovanna@beautyflow.ai": {"password": "123456", "name": "BeautyFlow Demo", "role": "Demonstração"},
}


def production() -> bool:
    return os.getenv("APP_ENV", "development").strip().lower() == "production"


def credentials_valid(email: str, password: str) -> bool:
    email = email.strip().lower()
    if production():
        configured_email = os.getenv("APP_LOGIN_EMAIL", "").strip().lower()
        password_hash = os.getenv("APP_LOGIN_PASSWORD_HASH", "")
        if not configured_email or not password_hash:
            return False
        return hmac.compare_digest(email.encode("utf-8"), configured_email.encode("utf-8")) and verify_password(password, password_hash)
    user = DEMO_USERS.get(email)
    return bool(user and hmac.compare_digest(user["password"].encode(), password.encode("utf-8")))


def init_auth_state() -> None:
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("user", None)


def login_user(email: str, password: str) -> bool:
    if not credentials_valid(email, password):
        return False
    user = {"name": "Administrador BeautyFlow", "role": "Administrador"} if production() else DEMO_USERS[email.strip().lower()]
    st.session_state.authenticated = True
    st.session_state.user = {"email": email.strip().lower(), "name": user["name"], "role": user["role"]}
    return True


def logout_user() -> None:
    st.session_state.authenticated = False
    st.session_state.user = None
    st.rerun()


def render_login_page() -> None:
    apply_login_styles()
    st.markdown("<h1 style='text-align:center;'>💎 BeautyFlow AI</h1>", unsafe_allow_html=True)
    st.caption("Gestão inteligente para negócios de beleza.")
    if production() and (not os.getenv("APP_LOGIN_EMAIL") or not os.getenv("APP_LOGIN_PASSWORD_HASH")):
        st.error("Acesso não configurado. Defina APP_LOGIN_EMAIL e APP_LOGIN_PASSWORD_HASH no servidor.")
        st.stop()
    with st.container(border=True):
        st.markdown("## Entrar no painel")
        with st.form("login_form"):
            email = st.text_input("E-mail")
            password = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                if login_user(email, password):
                    st.rerun()
                st.error("E-mail ou senha incorretos.")
        if not production():
            st.info("Acesso local demonstrativo: geovanna@beautyflow.ai / 123456")
