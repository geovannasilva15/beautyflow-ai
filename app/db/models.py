from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel

from app.core.time import utc_now


class AppointmentStatus(str, Enum):
    scheduled = "scheduled"
    completed = "completed"
    canceled = "canceled"
    no_show = "no_show"


class CampaignStatus(str, Enum):
    draft = "draft"
    scheduled = "scheduled"
    sent = "sent"
    canceled = "canceled"


class ConversationIntent(str, Enum):
    schedule = "agendar"
    cancel = "cancelar"
    reschedule = "reagendar"
    question = "duvida"
    promotion = "promocao"
    unknown = "desconhecido"


class Client(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    phone: str = Field(index=True)
    email: Optional[str] = None
    hair_type: Optional[str] = None
    skin_type: Optional[str] = None
    interests: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)


class Service(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    category: str
    description: str
    duration_minutes: int = 60
    price: float = 0.0
    tags: Optional[str] = None
    active: bool = True
    created_at: datetime = Field(default_factory=utc_now)


class Professional(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    specialty: str
    active: bool = True
    created_at: datetime = Field(default_factory=utc_now)


class Appointment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="client.id", index=True)
    service_id: int = Field(foreign_key="service.id", index=True)
    professional_id: int = Field(foreign_key="professional.id", index=True)
    duration_minutes: int | None = None
    scheduled_at: datetime = Field(index=True)
    final_price: float = 0.0
    status: AppointmentStatus = Field(default=AppointmentStatus.scheduled, index=True)
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)


class ConversationMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    client_name: str
    client_phone: str = Field(index=True)
    incoming_message: str
    detected_intent: ConversationIntent = Field(default=ConversationIntent.unknown, index=True)
    ai_response: str
    action_status: str = "simulated"
    appointment_id: Optional[int] = Field(default=None, foreign_key="appointment.id")
    created_at: datetime = Field(default_factory=utc_now)


class Campaign(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    message: str
    target_audience: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    status: CampaignStatus = Field(default=CampaignStatus.draft, index=True)
    created_at: datetime = Field(default_factory=utc_now)


class ScheduledMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    campaign_id: Optional[int] = Field(default=None, foreign_key="campaign.id")
    client_id: Optional[int] = Field(default=None, foreign_key="client.id")
    client_phone: str
    message: str
    scheduled_at: Optional[datetime] = None
    status: str = "pending"
    created_at: datetime = Field(default_factory=utc_now)


class AgentConfirmation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    token_hash: str = Field(index=True, unique=True)
    action_hash: str
    expires_at: datetime
    consumed: bool = False
    created_at: datetime = Field(default_factory=utc_now)


class Account(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=254)
    name: str = Field(max_length=120)
    password_hash: str = Field(max_length=160)
    role: str = Field(max_length=16)
    active: bool = True
    must_change_password: bool = False


class LoginSession(SQLModel, table=True):
    token_hash: str = Field(primary_key=True, max_length=64)
    account_id: int = Field(foreign_key="account.id", index=True)
    expires_at: datetime = Field(index=True)


class LoginLimit(SQLModel, table=True):
    key: str = Field(primary_key=True, max_length=64)
    attempts: int = 0
    expires_at: datetime = Field(index=True)


class WhatsAppMessage(SQLModel, table=True):
    provider_id: str = Field(primary_key=True, max_length=255)
    sender: str = Field(max_length=15)
    body: str
    received_at: datetime = Field(index=True)
    intent: str = Field(max_length=24)
    reply_status: str = Field(default="pending", max_length=16)
    reply_text: str | None = None
    reply_provider_id: str | None = Field(default=None, max_length=255)
