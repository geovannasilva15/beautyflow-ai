from __future__ import annotations

import pandas as pd
import streamlit as st

from frontend.api_client import api_delete, api_get, api_post, api_put, format_currency
from frontend.components import page_header


def render() -> None:
    st.markdown('<div class="bf-eyebrow">BEAUTYFLOW / SERVIÇOS</div><h1 class="bf-title">Serviços com personalidade.</h1><p class="bf-subtitle">Organize procedimentos, preços e duração.</p>', unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("### Cadastrar novo serviço")
        with st.form("service_create", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name = c1.text_input("Nome do serviço", placeholder="Ex: Hidratação profunda")
            category = c1.text_input("Categoria", placeholder="Ex: Cabelo")
            duration = c1.number_input("Duração em minutos", min_value=10, value=60, step=5)
            price = c2.number_input("Preço", min_value=0.0, value=120.0, step=10.0)
            tags = c2.text_input("Tags", placeholder="cabelo hidratação brilho frizz")
            description = st.text_area("Descrição", placeholder="Explique o benefício do serviço para a cliente.")

            if st.form_submit_button("Salvar serviço"):
                if not name or not category or not description:
                    st.warning("Nome, categoria e descrição são obrigatórios.")
                else:
                    api_post(
                        "/services",
                        json={
                            "name": name,
                            "category": category,
                            "description": description,
                            "duration_minutes": int(duration),
                            "price": float(price),
                            "tags": tags or None,
                        },
                    )
                    st.success("Serviço cadastrado com sucesso.")
                    st.rerun()

    services = pd.DataFrame(api_get("/services"))
    if services.empty:
        st.info("Nenhum serviço cadastrado ainda.")
        return

    st.metric("Serviços ativos", len(services))
    st.markdown("### Catálogo de serviços")
    search = st.text_input("Buscar por nome, categoria ou tag", placeholder="Ex: cabelo, pele, sobrancelha...")
    filtered = services.copy()
    if search:
        term = search.lower()
        filtered = filtered[
            filtered.apply(lambda row: term in " ".join(str(value).lower() for value in row.values), axis=1)
        ]

    if filtered.empty:
        st.warning("Nenhum serviço encontrado com esse filtro.")
        return

    for _, service in filtered.iterrows():
        service_id = int(service["id"])
        with st.container(border=True):
            top, actions = st.columns([0.72, 0.28])
            with top:
                st.markdown(f"### 💇 {service['name']}")
                st.write(service.get("description") or "Sem descrição.")
                st.caption(f"Categoria: {service.get('category', 'Não informada')} · Tags: {service.get('tags') or 'Sem tags'}")
            with actions:
                st.metric("Preço", format_currency(service.get("price")))
                st.metric("Duração", f"{int(service.get('duration_minutes', 0))} min")

            with st.expander("Editar serviço"):
                with st.form(f"service_edit_{service_id}"):
                    c1, c2 = st.columns(2)
                    edit_name = c1.text_input("Nome", value=str(service.get("name") or ""), key=f"sn_{service_id}")
                    edit_category = c1.text_input("Categoria", value=str(service.get("category") or ""), key=f"sc_{service_id}")
                    edit_duration = c1.number_input(
                        "Duração em minutos",
                        min_value=10,
                        value=int(service.get("duration_minutes") or 60),
                        step=5,
                        key=f"sd_{service_id}",
                    )
                    edit_price = c2.number_input(
                        "Preço",
                        min_value=0.0,
                        value=float(service.get("price") or 0),
                        step=10.0,
                        key=f"sp_{service_id}",
                    )
                    edit_tags = c2.text_input("Tags", value=str(service.get("tags") or ""), key=f"st_{service_id}")
                    edit_description = st.text_area(
                        "Descrição",
                        value=str(service.get("description") or ""),
                        key=f"sdesc_{service_id}",
                    )
                    active = st.checkbox("Serviço ativo", value=bool(service.get("active", True)), key=f"sa_{service_id}")

                    if st.form_submit_button("Atualizar serviço"):
                        api_put(
                            f"/services/{service_id}",
                            json={
                                "name": edit_name,
                                "category": edit_category,
                                "description": edit_description,
                                "duration_minutes": int(edit_duration),
                                "price": float(edit_price),
                                "tags": edit_tags or None,
                                "active": active,
                            },
                        )
                        st.success("Serviço atualizado com sucesso.")
                        st.rerun()

            with st.expander("Desativar serviço"):
                st.warning("A desativação remove o serviço da listagem principal, sem apagar o histórico.")
                if st.button("Desativar", key=f"service_delete_{service_id}"):
                    api_delete(f"/services/{service_id}")
                    st.success("Serviço desativado.")
                    st.rerun()
