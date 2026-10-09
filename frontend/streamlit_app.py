from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.api_client import api_online  # noqa: E402
from frontend.auth import init_auth_state, logout_user, render_login_page  # noqa: E402
from frontend.pages import agenda, assistente, atendimento_ia, campanhas, clientes, dashboard, home, recomendador, servicos  # noqa: E402
from frontend.styles import apply_global_styles  # noqa: E402

st.set_page_config(page_title="BeautyFlow AI", page_icon="💎", layout="wide", initial_sidebar_state="expanded")
apply_global_styles()

init_auth_state()
if st.query_params.get("logout") == "1":
    st.session_state.authenticated = False
    st.session_state.user = None
    st.query_params.clear()
    st.rerun()

if not st.session_state.authenticated:
    render_login_page()
    st.stop()

PAGES = {
    "Dashboard": dashboard.render,
    "Início": home.render,
    "Agenda": agenda.render,
    "Clientes": clientes.render,
    "Serviços": servicos.render,
    "Assistente IA": assistente.render,
    "Recomendador": recomendador.render,
    "Atendimento IA": atendimento_ia.render,
    "Campanhas": campanhas.render,
}

with st.sidebar:
    st.markdown("## 💎 BeautyFlow AI")
    st.caption("Agenda, IA e campanhas para negócios de beleza.")
    if st.button("Sair da conta"):
        logout_user()
    st.write("---")
    user = st.session_state.user or {}
    st.write(f"**Usuária:** {user.get('name', 'Demo')}")
    st.caption(user.get("role", "Demo"))
    st.write("---")
    if st.session_state.get("bf_page") not in PAGES:
        st.session_state["bf_page"] = "Dashboard"
    selected_page = st.radio(
        "Menu", list(PAGES.keys()), label_visibility="collapsed",
        key="bf_page",
    )
    st.write("---")
    if api_online():
        st.success("API conectada")
    else:
        st.error("API offline")
        st.caption("Rode: python -m uvicorn app.main:app --reload")

if not api_online():
    st.error("API não encontrada. Abra outro terminal e rode:")
    st.code("python -m uvicorn app.main:app --reload", language="powershell")
    st.stop()

PAGES[selected_page]()
