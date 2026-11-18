from __future__ import annotations

import streamlit as st

from frontend.api_client import BeautyFlowAPIError, api_post
from frontend.styles import apply_login_styles


def clear_auth_state() -> None:
    st.session_state.clear()


def logout_user() -> None:
    try:
        api_post("/auth/logout")
    except BeautyFlowAPIError:
        st.warning("A sessão no servidor expira automaticamente se a API estiver indisponível.")
    clear_auth_state()
    st.rerun()


def render_login_page() -> None:
    apply_login_styles()
    st.markdown("<h1 style='text-align:center;'>💎 BeautyFlow AI</h1>", unsafe_allow_html=True)
    st.caption("Gestão inteligente para negócios de beleza.")
    with st.container(border=True):
        st.markdown("## Entrar no painel")
        with st.form("login_form", clear_on_submit=True):
            email = st.text_input("E-mail")
            password = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                try:
                    result = api_post("/auth/login", json={"email": email, "password": password})
                except BeautyFlowAPIError as exc:
                    st.error(str(exc))
                else:
                    st.session_state["access_token"] = result["access_token"]
                    st.session_state["user"] = result["account"]
                    st.rerun()
