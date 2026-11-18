from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.api_client import BeautyFlowAPIError, api_get  # noqa: E402
from frontend.auth import clear_auth_state, logout_user, render_login_page  # noqa: E402
from frontend.pages import agenda, assistente, atendimento_ia, campanhas, clientes, contas, dashboard, home, recomendador, servicos  # noqa: E402
from frontend.styles import apply_global_styles  # noqa: E402

st.set_page_config(page_title="BeautyFlow AI", page_icon="💎", layout="wide", initial_sidebar_state="auto")
apply_global_styles()

if st.query_params.get("logout") == "1":
    st.query_params.clear()
    logout_user()

if not st.session_state.get("access_token"):
    render_login_page()
    st.stop()

try:
    user = api_get("/auth/me")
except BeautyFlowAPIError as exc:
    if exc.status_code == 401:
        clear_auth_state()
        st.rerun()
    st.error(str(exc))
    st.stop()
st.session_state["user"] = user

PAGES = {
    "Dashboard": dashboard.render,
    "Início": home.render,
    "Agenda": agenda.render,
    "Clientes": clientes.render,
    "Serviços": servicos.render,
    "Assistente IA": assistente.render,
    "Recomendador": recomendador.render,
    "Atendimento": atendimento_ia.render,
    "Campanhas": campanhas.render,
    "Minha conta": contas.render,
}

if user["must_change_password"]:
    PAGES = {"Minha conta": contas.render}
    st.info("Troque a senha inicial para acessar o painel.")

with st.sidebar:
    st.markdown("## 💎 BeautyFlow AI")
    st.text(user["name"])
    st.caption("Administrador" if user["role"] == "admin" else "Profissional")
    target = st.session_state.pop("navigate_to", st.session_state.get("bf_page"))
    if target in PAGES:
        st.session_state["bf_page"] = target
    elif st.session_state.get("bf_page") not in PAGES:
        st.session_state["bf_page"] = next(iter(PAGES))
    selected_page = st.radio("Menu", list(PAGES), label_visibility="collapsed", key="bf_page")
    if st.button("Sair da conta"):
        logout_user()

try:
    PAGES[selected_page]()
except BeautyFlowAPIError as exc:
    st.error(str(exc))
