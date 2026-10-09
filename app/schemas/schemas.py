from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.core.time import local_datetime_to_utc
from app.db.models import AppointmentStatus, CampaignStatus, ConversationIntent


class ClientCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=8, max_length=30)
    email: Optional[str] = None
    hair_type: Optional[str] = None
    skin_type: Optional[str] = None
    interests: Optional[str] = None
    notes: Optional[str] = None


class ClientUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    phone: Optional[str] = Field(default=None, min_length=8, max_length=30)
    email: Optional[str] = None
    hair_type: Optional[str] = None
    skin_type: Optional[str] = None
    interests: Optional[str] = None
    notes: Optional[str] = None


class ServiceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=3)
    duration_minutes: int = Field(default=60, ge=15, le=480)
    price: float = Field(default=0.0, ge=0)
    tags: Optional[str] = None


class ServiceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    category: Optional[str] = Field(default=None, min_length=2, max_length=80)
    description: Optional[str] = Field(default=None, min_length=3)
    duration_minutes: Optional[int] = Field(default=None, ge=15, le=480)
    price: Optional[float] = Field(default=None, ge=0)
    tags: Optional[str] = None
    active: Optional[bool] = None


class ProfessionalCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    specialty: str = Field(min_length=2, max_length=120)


class AppointmentCreate(BaseModel):
    client_id: int
    service_id: int
    professional_id: int
    scheduled_at: datetime
    final_price: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = None

    @field_validator("scheduled_at")
    @classmethod
    def normalize_scheduled_at(cls, value: datetime) -> datetime:
        return local_datetime_to_utc(value)


class AppointmentReschedule(BaseModel):
    scheduled_at: datetime

    @field_validator("scheduled_at")
    @classmethod
    def normalize_scheduled_at(cls, value: datetime) -> datetime:
        return local_datetime_to_utc(value)


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
        return local_datetime_to_utc(value) if value else None


class CampaignUpdate(BaseModel):
    title: Optional[str] = None
    message: Optional[str] = None
    target_audience: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[CampaignStatus] = None

    @field_validator("scheduled_at")
    @classmethod
    def normalize_scheduled_at(cls, value: Optional[datetime]) -> Optional[datetime]:
        return local_datetime_to_utc(value) if value else None
