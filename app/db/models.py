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
