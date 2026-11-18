from __future__ import annotations

import streamlit as st

from frontend.api_client import api_get, api_post
from frontend.components import page_header


def render() -> None:
    page_header("Atendimento", "Caixa de entrada do WhatsApp de testes.")
    if st.session_state.user["role"] != "admin":
        st.info("A caixa de entrada fica disponível à administração.")
        return

    status = api_get("/whatsapp/status")
    if not status["configured"]:
        st.info("Integração oficial ainda sem configuração. Consulte as instruções de implantação.")
    else:
        st.caption("Respostas disponíveis somente para os números autorizados no piloto.")
    messages = api_get("/whatsapp/inbox")
    if not messages:
        st.info("Nenhuma mensagem recebida do WhatsApp.")
        return

    for item in messages:
        message_id = item["provider_id"]
        with st.expander(f"+{item['sender']} · {item['intent']} · {item['received_at'][:16]} UTC"):
            st.text(item["body"])
            st.caption({
                "pending": "Aguardando resposta",
                "sending": "Envio em andamento ou sem confirmação",
                "sent": "Aceita pela Meta",
                "unknown": "Envio sem confirmação",
                "rejected": "Envio recusado",
            }.get(item["reply_status"], item["reply_status"]))
            if item.get("reply_text"):
                st.text(item["reply_text"])
            if item["intent"] in {"agendar", "cancelar", "reagendar"}:
                st.caption("Consulte a Agenda e confirme os detalhes com a cliente antes de alterar o horário.")
                if st.button("Abrir agenda", key=f"open_agenda_{message_id}"):
                    st.session_state["navigate_to"] = "Agenda"
                    st.rerun()
            if status["configured"] and item["reply_status"] in {"pending", "rejected"}:
                with st.form(f"reply_{message_id}", clear_on_submit=True):
                    text = st.text_area("Resposta", max_chars=4096)
                    confirm = st.checkbox(f"Confirmo o envio para +{item['sender']}")
                    if st.form_submit_button("Enviar resposta de teste"):
                        api_post(f"/whatsapp/inbox/{message_id}/reply", json={"text": text, "confirm": confirm})
                        st.rerun()
