from __future__ import annotations

import streamlit as st

from frontend.api_client import api_delete, api_get, api_post
from frontend.auth import clear_auth_state


def render() -> None:
    st.header("Minha conta")
    with st.form("change_password", clear_on_submit=True):
        current = st.text_input("Senha atual", type="password")
        new = st.text_input("Nova senha", type="password", help="Use de 16 a 128 caracteres.")
        repeat = st.text_input("Repita a nova senha", type="password")
        if st.form_submit_button("Alterar senha"):
            if new != repeat:
                st.error("As senhas não coincidem.")
            else:
                api_post("/auth/password", json={"current_password": current, "new_password": new})
                clear_auth_state()
                st.rerun()

    if st.session_state.user["role"] != "admin" or st.session_state.user["must_change_password"]:
        return

    st.header("Contas da equipe")
    with st.form("create_account", clear_on_submit=True):
        name = st.text_input("Nome")
        email = st.text_input("E-mail")
        role = st.selectbox(
            "Perfil", ["professional", "admin"],
            format_func=lambda role: {"professional": "Profissional", "admin": "Administrador"}[role],
        )
        password = st.text_input("Senha inicial", type="password", help="Use de 16 a 128 caracteres.")
        if st.form_submit_button("Criar conta"):
            api_post("/auth/accounts", json={"name": name, "email": email, "role": role, "password": password})
            st.success("Conta criada. Oriente a pessoa a trocar a senha ao entrar.")

    accounts = api_get("/auth/accounts")
    st.dataframe(
        [
            {"Nome": account["name"], "E-mail": account["email"],
             "Perfil": "Administrador" if account["role"] == "admin" else "Profissional",
             "Ativa": account["active"]}
            for account in accounts
        ],
        hide_index=True,
    )
    others = [account for account in accounts if account["active"] and account["id"] != st.session_state.user["id"]]
    if others:
        with st.form("disable_account"):
            account = st.selectbox("Conta para desativar", others, format_func=lambda item: item["email"])
            if st.form_submit_button("Desativar conta"):
                api_delete(f"/auth/accounts/{account['id']}")
                st.rerun()
