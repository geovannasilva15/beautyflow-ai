from __future__ import annotations

import streamlit as st

from frontend.api_client import BeautyFlowAPIError, api_post
from frontend.components import page_header


def render() -> None:
    page_header("Assistente IA", "Crie respostas, mensagens e campanhas profissionais.")

    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.markdown("### Mentora de gestão")
            context = st.text_input("Contexto do negócio", "salão de beleza com agenda via WhatsApp")
            question = st.text_area("Pergunta", "Como reduzir faltas nos agendamentos?", height=120)
            if st.button("Perguntar", key="ai_chat"):
                try:
                    result = api_post("/ai/chat", json={"question": question, "business_context": context})
                    st.markdown(result["answer"])
                except BeautyFlowAPIError as exc:
                    st.error(str(exc))

        with st.container(border=True):
            st.markdown("### Mensagem para cliente")
            goal = st.text_input("Objetivo", "confirmar agendamento")
            profile = st.text_input("Perfil da cliente", "cliente recorrente interessada em hidratação")
            tone = st.text_input("Tom", "profissional e acolhedor")
            if st.button("Gerar mensagem", key="ai_message"):
                result = api_post("/ai/message", json={"goal": goal, "client_profile": profile, "tone": tone})
                st.success(result["message"])

    with col2:
        with st.container(border=True):
            st.markdown("### Post de campanha")
            service = st.text_input("Serviço", "Hidratação Profunda")
            audience = st.text_input("Público", "clientes com cabelo ressecado, frizz ou falta de brilho")
            objective = st.text_area("Objetivo da campanha", "Atrair agendamentos para a semana e preencher horários vagos.", height=100)
            if st.button("Gerar post", key="ai_marketing"):
                result = api_post(
                    "/ai/marketing-post",
                    json={"service_name": service, "target_audience": audience, "campaign_goal": objective},
                )
                st.markdown(result["post"])

        with st.container(border=True):
            st.markdown("### Sugestões de uso")
            st.write("• Criar respostas rápidas para WhatsApp.")
            st.write("• Transformar dúvidas em oportunidades de agendamento.")
            st.write("• Criar mensagens para campanhas segmentadas.")
            st.write("• Apoiar a rotina de atendimento sem perder o tom humano.")
