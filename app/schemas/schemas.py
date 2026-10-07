from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.core.time import ensure_utc
from app.db.models import AppointmentStatus, CampaignStatus, ConversationIntent


class ClientCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    hair_type: Optional[str] = None
    skin_type: Optional[str] = None
    interests: Optional[str] = None
    notes: Optional[str] = None


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    hair_type: Optional[str] = None
    skin_type: Optional[str] = None
    interests: Optional[str] = None
    notes: Optional[str] = None


class ServiceCreate(BaseModel):
    name: str
    category: str
    description: str
    duration_minutes: int = 60
    price: float = 0.0
    tags: Optional[str] = None


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    price: Optional[float] = None
    tags: Optional[str] = None
    active: Optional[bool] = None


class ProfessionalCreate(BaseModel):
    name: str
    specialty: str


class AppointmentCreate(BaseModel):
    client_id: int
    service_id: int
    professional_id: int
    scheduled_at: datetime
    final_price: Optional[float] = None
    notes: Optional[str] = None

    @field_validator("scheduled_at")
    @classmethod
    def normalize_scheduled_at(cls, value: datetime) -> datetime:
        return ensure_utc(value)


class AppointmentUpdateStatus(BaseModel):
    status: AppointmentStatus


class AIChatRequest(BaseModel):
    question: str
    business_context: str


class AIMessageRequest(BaseModel):
    goal: str
    client_profile: str
    tone: str = "profissional, simpático e objetivo"


class MarketingPostRequest(BaseModel):
    service_name: str
    target_audience: str
    campaign_goal: str


class RecommendationRequest(BaseModel):
    client_profile: str
    top_k: int = Field(default=3, ge=1, le=10)


class WhatsAppSimulationRequest(BaseModel):
    client_name: str = "Cliente BeautyFlow"
    client_phone: str
    message: str


class WhatsAppSimulationResponse(BaseModel):
    intent: ConversationIntent
    response: str
    action_status: str
    action_suggested: Optional[str] = None
    appointment_id: Optional[int] = None


class CampaignCreate(BaseModel):
    title: str
    message: str
    target_audience: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    status: CampaignStatus = CampaignStatus.scheduled

    @field_validator("scheduled_at")
    @classmethod
    def normalize_scheduled_at(cls, value: Optional[datetime]) -> Optional[datetime]:
        return ensure_utc(value) if value else None


class CampaignUpdate(BaseModel):
    title: Optional[str] = None
    message: Optional[str] = None
    target_audience: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[CampaignStatus] = None

    @field_validator("scheduled_at")
    @classmethod
    def normalize_scheduled_at(cls, value: Optional[datetime]) -> Optional[datetime]:
        return ensure_utc(value) if value else None
