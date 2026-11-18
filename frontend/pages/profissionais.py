from __future__ import annotations

import streamlit as st

from frontend.api_client import api_get, api_post, api_put


def render_professionals() -> None:
    with st.expander("Gerenciar profissionais"):
        with st.form("professional_create", clear_on_submit=True):
            name = st.text_input("Nome", max_chars=120)
            specialty = st.text_input("Especialidade", max_chars=120)
            if st.form_submit_button("Cadastrar profissional"):
                api_post("/professionals", json={"name": name, "specialty": specialty})
                st.rerun()

        professionals = api_get("/professionals", params={"active_only": False})
        if not professionals:
            return
        selected = st.selectbox(
            "Profissional para editar", professionals,
            format_func=lambda item: f"{item['name']} · #{item['id']}",
        )
        with st.form(f"professional_edit_{selected['id']}"):
            name = st.text_input("Nome", value=selected["name"], max_chars=120)
            specialty = st.text_input("Especialidade", value=selected["specialty"], max_chars=120)
            active = st.checkbox("Ativo na agenda", value=selected["active"])
            if st.form_submit_button("Salvar profissional"):
                api_put(f"/professionals/{selected['id']}", json={"name": name, "specialty": specialty, "active": active})
                st.rerun()
