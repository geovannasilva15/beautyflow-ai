from __future__ import annotations

from datetime import date, datetime, time, timedelta

import streamlit as st

from app.core.time import business_now
from frontend.api_client import api_get, api_post, format_currency
from frontend.components import page_header


def render() -> None:
    page_header("Assistente", "Orientação de gestão, consultas e ações na agenda.")
    chat, system, templates = st.tabs(["Mentora de IA", "Dados do sistema", "Modelos de texto"])
    with chat:
        st.caption("A IA oferece orientações gerais. Use dados fictícios no texto enviado ao provedor.")
        with st.form("ai_chat"):
            context = st.text_input("Contexto do negócio", max_chars=1500, placeholder="Exemplo: salão com três profissionais")
            question = st.text_area("Pergunta", max_chars=1500, placeholder="Como reduzir faltas?")
            if st.form_submit_button("Perguntar"):
                result = api_post("/ai/chat", json={"question": question, "business_context": context})
                st.text(result["answer"])

    with system:
        render_system_tools()

    with templates:
        st.caption("Textos montados a partir de modelos fixos.")
        with st.form("ai_message"):
            goal = st.text_input("Objetivo")
            profile = st.text_input("Perfil da cliente")
            tone = st.text_input("Tom", "profissional e acolhedor")
            if st.form_submit_button("Gerar mensagem"):
                result = api_post("/ai/message", json={"goal": goal, "client_profile": profile, "tone": tone})
                st.write(result["message"])

        with st.form("ai_marketing"):
            service = st.text_input("Serviço")
            audience = st.text_input("Público")
            objective = st.text_area("Objetivo da campanha", height=100)
            if st.form_submit_button("Gerar post"):
                result = api_post(
                    "/ai/marketing-post",
                    json={"service_name": service, "target_audience": audience, "campaign_goal": objective},
                )
                st.write(result["post"])


def day_and_time(default_day: date) -> datetime:
    day = st.date_input("Data", default_day, key="helper_day")
    hour = st.time_input("Horário", time(14), key="helper_hour")
    return datetime.combine(day, hour)


def render_system_tools() -> None:
    labels = {
        "list_services": "Consultar preços e serviços",
        "find_client": "Localizar cliente",
        "availability": "Consultar horários livres",
        "book": "Agendar",
        "reschedule": "Reagendar",
        "cancel": "Cancelar",
    }
    tool = st.selectbox("Operação", list(labels), format_func=labels.get)
    request = {"tool": tool}
    tomorrow = business_now().date() + timedelta(days=1)
    if tool == "find_client":
        request["query"] = st.text_input("Nome", max_chars=120, key="helper_search")
    if tool in {"availability", "book"}:
        services = api_get("/services")
        professionals = api_get("/professionals")
        if not services or not professionals:
            st.info("Cadastre serviços e profissionais ativos para consultar ou reservar horários.")
            return
        service = st.selectbox("Serviço", services, format_func=lambda item: f"{item['name']} · #{item['id']}")
        professional = st.selectbox("Profissional", professionals, format_func=lambda item: f"{item['name']} · #{item['id']}")
        request.update(service_id=service["id"], professional_id=professional["id"])
        if tool == "availability":
            day = st.date_input("Data da consulta", tomorrow)
            request["scheduled_at"] = datetime.combine(day, time.min).isoformat()
        else:
            clients = api_get("/clients")
            if not clients:
                st.info("Cadastre uma cliente para criar o agendamento.")
                return
            client = st.selectbox("Cliente", clients, format_func=lambda item: f"{item['name']} · #{item['id']}")
            request.update(client_id=client["id"], scheduled_at=day_and_time(tomorrow).isoformat())
    if tool in {"cancel", "reschedule"}:
        appointments = [item for item in api_get("/appointments") if item["status"] == "scheduled"]
        if not appointments:
            st.info("Nenhum agendamento ativo.")
            return
        appointment = st.selectbox(
            "Agendamento", appointments, format_func=lambda item: f"#{item['id']} · {item['scheduled_at']}",
        )
        request["appointment_id"] = appointment["id"]
        if tool == "reschedule":
            request["scheduled_at"] = day_and_time(tomorrow).isoformat()

    writes = tool in {"book", "cancel", "reschedule"}
    if st.button("Revisar operação" if writes else "Consultar"):
        result = api_post("/agent/tools", json=request)
        st.session_state["assistant_result"] = (request, result)

    saved_request, result = st.session_state.get("assistant_result", ({}, {}))
    if saved_request != request:
        return
    status = result["status"]
    if status == "confirmation_required":
        preview = result["preview"]
        st.write(f"{labels[tool]} · {preview['client']} · {preview['service']} · {preview['professional']}")
        if preview.get("previous_at"):
            st.caption(f"Horário anterior: {format_time(preview['previous_at'])}")
        st.write(f"{format_time(preview['scheduled_at'])} · {format_currency(preview['price'])}")
        if st.button("Confirmar " + labels[tool].lower(), type="primary"):
            result = api_post("/agent/tools", json={
                **request, "confirm": True, "confirmation_token": result["confirmation_token"],
            })
            st.session_state["assistant_result"] = (request, result)
            st.rerun()
    elif status == "ok":
        if "slots" in result:
            st.write(" · ".join(format_time(slot) for slot in result["slots"]) or "Nenhum horário livre.")
        elif result["data"]:
            st.dataframe(result["data"], hide_index=True)
        else:
            st.info("Nenhum resultado.")
    elif status in {"created", "canceled", "rescheduled"}:
        st.success(f"Operação concluída no agendamento #{result['appointment_id']}.")
    else:
        st.warning(result.get("message") or "Operação indisponível. Confira os dados e faça uma nova revisão.")


def format_time(value: str) -> str:
    return datetime.fromisoformat(value).strftime("%d/%m/%Y às %H:%M")
