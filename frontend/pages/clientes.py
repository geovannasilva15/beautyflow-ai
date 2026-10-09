from __future__ import annotations

import pandas as pd
import streamlit as st

from frontend.api_client import api_delete, api_get, api_post, api_put, format_currency
from frontend.components import page_header


def render() -> None:
    st.markdown('<div class="bf-eyebrow">BEAUTYFLOW / CLIENTES</div><h1 class="bf-title">Relacionamentos que florescem.</h1><p class="bf-subtitle">Conheça suas clientes, acompanhe visitas e fortaleça a fidelização.</p>', unsafe_allow_html=True)
    crm = api_get("/crm/summary")
    m1, m2, m3 = st.columns(3)
    m1.metric("Clientes cadastrados", crm["total_clients"])
    m2.metric("Clientes recorrentes", crm["returning_clients"])
    m3.metric("Clientes inativos", crm["inactive_clients"])
    crm_by_id = {c["client_id"]: c for c in crm["customers"]}
    st.write("")
    with st.expander("Cadastrar novo cliente", expanded=True):
        with st.form("client_create"):
            c1, c2, c3 = st.columns(3)
            name = c1.text_input("Nome")
            phone = c1.text_input("Telefone")
            email = c2.text_input("E-mail")
            hair_type = c2.text_input("Tipo de cabelo")
            skin_type = c3.text_input("Tipo de pele")
            interests = c3.text_input("Interesses")
            notes = st.text_area("Observações")
            if st.form_submit_button("Salvar cliente"):
                if not name or not phone:
                    st.warning("Nome e telefone são obrigatórios.")
                else:
                    api_post("/clients", json={"name": name, "phone": phone, "email": email or None, "hair_type": hair_type or None, "skin_type": skin_type or None, "interests": interests or None, "notes": notes or None})
                    st.success("Cliente cadastrado.")
                    st.rerun()

    clients = api_get("/clients")
    df = pd.DataFrame(clients)
    if df.empty:
        st.info("Nenhum cliente cadastrado.")
        return
    search = st.text_input("Buscar cliente")
    if search:
        s = search.lower()
        df = df[df.apply(lambda row: s in " ".join(str(v).lower() for v in row.values), axis=1)]
    st.caption(f"{len(df)} cliente(s) encontrado(s)")
    for _, client in df.iterrows():
        client_id = int(client["id"])
        with st.container(border=True):
            st.markdown(f"### 👤 {client['name']}")
            profile = crm_by_id.get(client_id, {})
            x1, x2, x3 = st.columns(3)
            x1.metric("Visitas concluídas", profile.get("completed_visits", 0))
            x2.metric("Total realizado", format_currency(profile.get("total_spent", 0)))
            x3.metric("Serviço favorito", profile.get("favorite_service") or "—")
            if profile.get("last_visit"):
                st.caption("Última visita registrada: " + profile["last_visit"][:10])
            if profile.get("inactive"):
                st.caption("Sem visitas concluídas nos últimos 60 dias.")
            st.write(f"**Telefone:** {client.get('phone', '')}")
            st.write(f"**E-mail:** {client.get('email') or 'Não informado'}")
            st.write(f"**Interesses:** {client.get('interests') or 'Não informado'}")
            with st.expander("Editar"):
                with st.form(f"edit_{client_id}"):
                    name = st.text_input("Nome", value=str(client.get("name") or ""), key=f"n{client_id}")
                    phone = st.text_input("Telefone", value=str(client.get("phone") or ""), key=f"p{client_id}")
                    email = st.text_input("E-mail", value=str(client.get("email") or ""), key=f"e{client_id}")
                    interests = st.text_input("Interesses", value=str(client.get("interests") or ""), key=f"i{client_id}")
                    if st.form_submit_button("Atualizar"):
                        api_put(f"/clients/{client_id}", json={"name": name, "phone": phone, "email": email or None, "interests": interests or None})
                        st.success("Atualizado.")
                        st.rerun()
            with st.expander("Excluir"):
                if st.button("Excluir cliente", key=f"del{client_id}"):
                    try:
                        api_delete(f"/clients/{client_id}")
                        st.success("Excluído.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Erro: {exc}")
