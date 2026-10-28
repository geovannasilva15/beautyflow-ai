from __future__ import annotations

import hmac
import os

import streamlit as st

from frontend.styles import apply_login_styles

DEMO_USERS = {
    "geovanna@beautyflow.ai": {"password": "123456", "name": "BeautyFlow Demo", "role": "Demonstração"},
}


def _production() -> bool:
    return os.getenv("APP_ENV", "development").lower() == "production"


def _credential(name: str) -> str:
    try:
        return str(st.secrets.get(name) or os.getenv(name, ""))
    except Exception:
        return os.getenv(name, "")


def init_auth_state() -> None:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None


def login_user(email: str, password: str) -> bool:
    email = email.strip().lower()
    if _production():
        login_email = _credential("APP_LOGIN_EMAIL").strip().lower()
        login_password = _credential("APP_LOGIN_PASSWORD")
        if (
            not login_email
            or len(login_password) < 16
            or not hmac.compare_digest(email, login_email)
            or not hmac.compare_digest(password, login_password)
        ):
            return False
        user = {"name": "Administrador BeautyFlow", "role": "Administrador"}
    else:
        user = DEMO_USERS.get(email)
        if not user or not hmac.compare_digest(user["password"], password):
            return False

    st.session_state.authenticated = True
    st.session_state.user = {"email": email, "name": user["name"], "role": user["role"]}
    return True


def logout_user() -> None:
    st.session_state.authenticated = False
    st.session_state.user = None
    st.rerun()


def render_login_page() -> None:
    apply_login_styles()
    st.markdown("<h1 style='text-align:center;'>BeautyFlow AI</h1>", unsafe_allow_html=True)
    st.caption("Seu espaço de gestão inteligente para negócios de beleza.")
    if _production() and (not _credential("APP_LOGIN_EMAIL") or len(_credential("APP_LOGIN_PASSWORD")) < 16):
        st.error("Acesso não configurado. Defina APP_LOGIN_EMAIL e APP_LOGIN_PASSWORD (mínimo 16 caracteres) no servidor.")
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
        if not _production():
            st.info("Acesso local demonstrativo: geovanna@beautyflow.ai / 123456")
