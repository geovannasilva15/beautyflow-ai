from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.config import get_settings
from app.db.database import get_session
from app.db.models import Appointment, AppointmentStatus, Campaign, Client, ConversationMessage, Professional, ScheduledMessage, Service
from app.ml.recommender import recommend_services
from app.schemas.schemas import (
    AIChatRequest,
    AIMessageRequest,
    AppointmentCreate,
    AppointmentReschedule,
    AppointmentUpdateStatus,
    CampaignCreate,
    ClientCreate,
    ClientUpdate,
    MarketingPostRequest,
    ProfessionalCreate,
    RecommendationRequest,
    ServiceCreate,
    ServiceUpdate,
    WhatsAppSimulationRequest,
)
from app.services.ai_service import AIProviderUnavailable, generate_ai_answer, generate_client_message, generate_marketing_post
from app.services.analytics_service import get_dashboard_metrics
from app.services.appointment_service import appointment_slot_error, get_available_slots
from app.services.campaign_service import create_campaign, schedule_campaign_messages
from app.services.crm_service import get_crm_metrics
from app.services.agent_tools import AgentToolRequest, execute_agent_tool
from app.services.whatsapp_agent_service import process_whatsapp_message

router = APIRouter()
settings = get_settings()


@router.get("/health")
def health_check() -> dict:
    return {
        "status": "ok",
        "message": "BeautyFlow AI API está funcionando.",
        "timezone": settings.business_timezone,
    }


@router.post("/clients", response_model=Client)
def create_client(payload: ClientCreate, session: Session = Depends(get_session)) -> Client:
    client = Client(**payload.model_dump())
    session.add(client)
    session.commit()
    session.refresh(client)
    return client


@router.get("/clients", response_model=list[Client])
def list_clients(session: Session = Depends(get_session)) -> list[Client]:
    return session.exec(select(Client).order_by(Client.created_at.desc())).all()


@router.put("/clients/{client_id}", response_model=Client)
def update_client(client_id: int, payload: ClientUpdate, session: Session = Depends(get_session)) -> Client:
    client = session.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    session.add(client)
    session.commit()
    session.refresh(client)
    return client


@router.delete("/clients/{client_id}")
def delete_client(client_id: int, session: Session = Depends(get_session)) -> dict:
    client = session.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    has_appointment = session.exec(select(Appointment).where(Appointment.client_id == client_id)).first()
    if has_appointment:
        raise HTTPException(status_code=400, detail="Cliente possui agendamentos vinculados e não pode ser excluído.")
    session.delete(client)
    session.commit()
    return {"message": "Cliente excluído com sucesso."}


@router.post("/services", response_model=Service)
def create_service(payload: ServiceCreate, session: Session = Depends(get_session)) -> Service:
    service = Service(**payload.model_dump())
    session.add(service)
    session.commit()
    session.refresh(service)
    return service


@router.get("/services", response_model=list[Service])
def list_services(session: Session = Depends(get_session)) -> list[Service]:
    return session.exec(select(Service).where(Service.active == True).order_by(Service.name)).all()  # noqa: E712


@router.put("/services/{service_id}", response_model=Service)
def update_service(service_id: int, payload: ServiceUpdate, session: Session = Depends(get_session)) -> Service:
    service = session.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Serviço não encontrado.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(service, field, value)
    session.add(service)
    session.commit()
    session.refresh(service)
    return service


@router.delete("/services/{service_id}")
def delete_service(service_id: int, session: Session = Depends(get_session)) -> dict:
    service = session.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Serviço não encontrado.")
    service.active = False
    session.add(service)
    session.commit()
    return {"message": "Serviço desativado com sucesso."}


@router.post("/professionals", response_model=Professional)
def create_professional(payload: ProfessionalCreate, session: Session = Depends(get_session)) -> Professional:
    professional = Professional(**payload.model_dump())
    session.add(professional)
    session.commit()
    session.refresh(professional)
    return professional


@router.get("/professionals", response_model=list[Professional])
def list_professionals(session: Session = Depends(get_session)) -> list[Professional]:
    return session.exec(select(Professional).where(Professional.active == True).order_by(Professional.name)).all()  # noqa: E712


@router.get("/appointments/availability")
def appointment_availability(
    professional_id: int,
    service_id: int,
    target_date: date,
    session: Session = Depends(get_session),
) -> dict:
    professional = session.get(Professional, professional_id)
    service = session.get(Service, service_id)
    if not professional or not professional.active:
        raise HTTPException(status_code=404, detail="Profissional não encontrado ou inativo.")
    if not service or not service.active:
        raise HTTPException(status_code=404, detail="Serviço não encontrado ou inativo.")

    slots = get_available_slots(session, professional_id, service_id, target_date)
    return {
        "date": target_date.isoformat(),
        "timezone": settings.business_timezone,
        "slots": [slot.isoformat() for slot in slots],
    }


@router.post("/appointments", response_model=Appointment)
def create_appointment(payload: AppointmentCreate, session: Session = Depends(get_session)) -> Appointment:
    client = session.get(Client, payload.client_id)
    service = session.get(Service, payload.service_id)
    professional = session.get(Professional, payload.professional_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    if not service or not service.active:
        raise HTTPException(status_code=404, detail="Serviço não encontrado ou inativo.")
    if not professional or not professional.active:
        raise HTTPException(status_code=404, detail="Profissional não encontrado ou inativo.")

    error = appointment_slot_error(
        session,
        payload.professional_id,
        payload.service_id,
        payload.scheduled_at,
    )
    if error:
        raise HTTPException(status_code=409, detail=error)

    appointment = Appointment(
        client_id=payload.client_id,
        service_id=payload.service_id,
        professional_id=payload.professional_id,
        scheduled_at=payload.scheduled_at,
        final_price=payload.final_price if payload.final_price is not None else service.price,
        notes=payload.notes,
    )
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    return appointment


@router.get("/appointments", response_model=list[Appointment])
def list_appointments(session: Session = Depends(get_session)) -> list[Appointment]:
    return session.exec(select(Appointment).order_by(Appointment.scheduled_at.desc())).all()


@router.patch("/appointments/{appointment_id}/status", response_model=Appointment)
def update_appointment_status(
    appointment_id: int,
    payload: AppointmentUpdateStatus,
    session: Session = Depends(get_session),
) -> Appointment:
    appointment = session.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    appointment.status = payload.status
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    return appointment


@router.patch("/appointments/{appointment_id}/reschedule", response_model=Appointment)
def reschedule_appointment(
    appointment_id: int,
    payload: AppointmentReschedule,
    session: Session = Depends(get_session),
) -> Appointment:
    appointment = session.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    if appointment.status == AppointmentStatus.completed:
        raise HTTPException(status_code=409, detail="Um atendimento concluído não pode ser reagendado.")

    error = appointment_slot_error(
        session,
        appointment.professional_id,
        appointment.service_id,
        payload.scheduled_at,
        exclude_appointment_id=appointment.id,
    )
    if error:
        raise HTTPException(status_code=409, detail=error)

    appointment.scheduled_at = payload.scheduled_at
    appointment.status = AppointmentStatus.scheduled
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    return appointment


@router.post("/ai/chat")
def ai_chat(payload: AIChatRequest) -> dict:
    try:
        return {"answer": generate_ai_answer(payload.question, payload.business_context)}
    except AIProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/ai/message")
def ai_message(payload: AIMessageRequest) -> dict:
    return {"message": generate_client_message(payload.goal, payload.client_profile, payload.tone)}


@router.post("/ai/marketing-post")
def ai_marketing_post(payload: MarketingPostRequest) -> dict:
    return {"post": generate_marketing_post(payload.service_name, payload.target_audience, payload.campaign_goal)}


@router.post("/recommendations")
def recommendations(payload: RecommendationRequest, session: Session = Depends(get_session)) -> dict:
    return {"recommendations": recommend_services(session, payload.client_profile, payload.top_k)}


@router.post("/whatsapp/simulate")
def whatsapp_simulate(payload: WhatsAppSimulationRequest, session: Session = Depends(get_session)) -> dict:
    return process_whatsapp_message(session, payload.client_name, payload.client_phone, payload.message)


@router.get("/conversations", response_model=list[ConversationMessage])
def list_conversations(session: Session = Depends(get_session)) -> list[ConversationMessage]:
    return session.exec(select(ConversationMessage).order_by(ConversationMessage.created_at.desc())).all()


@router.post("/campaigns", response_model=Campaign)
def create_new_campaign(payload: CampaignCreate, session: Session = Depends(get_session)) -> Campaign:
    return create_campaign(session, payload)


@router.get("/campaigns", response_model=list[Campaign])
def list_campaigns(session: Session = Depends(get_session)) -> list[Campaign]:
    return session.exec(select(Campaign).order_by(Campaign.created_at.desc())).all()


@router.get("/scheduled-messages", response_model=list[ScheduledMessage])
def list_scheduled_messages(session: Session = Depends(get_session)) -> list[ScheduledMessage]:
    return session.exec(select(ScheduledMessage).order_by(ScheduledMessage.created_at.desc())).all()


@router.post("/campaigns/{campaign_id}/schedule")
def schedule_campaign(campaign_id: int, session: Session = Depends(get_session)) -> dict:
    return schedule_campaign_messages(session, campaign_id)


@router.post("/campaigns/{campaign_id}/simulate-send")
def simulate_campaign_send(campaign_id: int, session: Session = Depends(get_session)) -> dict:
    return schedule_campaign_messages(session, campaign_id)


@router.post("/agent/tools")
def agent_tools(payload: AgentToolRequest, session: Session = Depends(get_session)) -> dict:
    return execute_agent_tool(session, payload)


@router.get("/crm/summary")
def crm_summary(inactive_days: int = 60, session: Session = Depends(get_session)) -> dict:
    if not 1 <= inactive_days <= 365:
        raise HTTPException(status_code=422, detail="inactive_days deve estar entre 1 e 365.")
    return get_crm_metrics(session, inactive_days)


@router.get("/dashboard")
def dashboard(session: Session = Depends(get_session)) -> dict:
    return get_dashboard_metrics(session)
