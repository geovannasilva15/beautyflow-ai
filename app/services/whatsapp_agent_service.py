from __future__ import annotations

from sqlmodel import Session

from app.db.models import ConversationIntent, ConversationMessage
from app.services.appointment_service import (
    cancel_latest_appointment,
    create_appointment_from_message,
    find_service_from_text,
    reschedule_latest_appointment,
)


def detect_intent(message: str) -> ConversationIntent:
    text = message.lower()

    if any(word in text for word in ["remarcar", "reagendar", "outro horário", "outro horario"]):
        return ConversationIntent.reschedule
    if any(word in text for word in ["cancelar", "desmarcar", "não vou", "nao vou"]):
        return ConversationIntent.cancel
    if any(word in text for word in ["marcar", "agendar", "horário", "horario", "tem vaga", "disponível", "disponivel"]):
        return ConversationIntent.schedule
    if any(word in text for word in ["promo", "promoção", "promocao", "desconto", "oferta"]):
        return ConversationIntent.promotion
    if any(word in text for word in ["quanto", "valor", "preço", "preco", "serviço", "servico"]):
        return ConversationIntent.question
    return ConversationIntent.unknown


def process_whatsapp_message(session: Session, client_name: str, client_phone: str, message: str) -> dict:
    intent = detect_intent(message)
    appointment_id = None
    action_status = "responded"
    action_suggested = "Responder de forma acolhedora e registrar a conversa."

    if intent == ConversationIntent.schedule:
        response, appointment_id = create_appointment_from_message(session, client_name, client_phone, message)
        action_status = "appointment_created" if appointment_id else "appointment_suggestion"
        action_suggested = "Validar serviço, profissional e disponibilidade antes de criar o agendamento."

    elif intent == ConversationIntent.cancel:
        response, appointment_id = cancel_latest_appointment(session, client_phone)
        action_status = "appointment_canceled" if appointment_id else "cancel_not_found"
        action_suggested = "Cancelar o próximo agendamento futuro ou pedir mais dados para localizar a reserva."

    elif intent == ConversationIntent.reschedule:
        response, appointment_id, changed = reschedule_latest_appointment(session, client_phone, message)
        action_status = "appointment_rescheduled" if changed else "reschedule_suggested"
        action_suggested = "Sugerir horários realmente livres e atualizar o agendamento quando a cliente confirmar."

    elif intent == ConversationIntent.promotion:
        response = "Temos campanhas especiais disponíveis. Posso te ajudar a escolher um serviço e verificar horários livres."
        action_suggested = "Apresentar campanha ativa e transformar o interesse em agendamento."

    elif intent == ConversationIntent.question:
        service = find_service_from_text(session, message)
        if service:
            response = (
                f"O serviço {service.name} custa R$ {service.price:.2f} e dura cerca de "
                f"{service.duration_minutes} minutos. Quer que eu verifique horários disponíveis?"
            )
        else:
            response = "Posso te ajudar com valores e serviços. Qual procedimento você quer consultar?"
        action_suggested = "Responder com dados cadastrados no sistema e oferecer o próximo passo."

    else:
        response = "Oi! Sou a assistente do BeautyFlow AI. Posso ajudar com agendamentos, reagendamentos, cancelamentos, valores e promoções."
        action_suggested = "Pedir mais contexto se a intenção continuar indefinida."

    record = ConversationMessage(
        client_name=client_name,
        client_phone=client_phone,
        incoming_message=message,
        detected_intent=intent,
        ai_response=response,
        action_status=action_status,
        appointment_id=appointment_id,
    )
    session.add(record)
    session.commit()
    session.refresh(record)

    return {
        "intent": intent,
        "response": response,
        "action_status": action_status,
        "action_suggested": action_suggested,
        "appointment_id": appointment_id,
        "conversation_id": record.id,
    }
