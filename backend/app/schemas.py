import uuid
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RegisterIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8)
    tenant_name: str = Field(min_length=1, max_length=200)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    user_type: str
    is_active: bool
    permissions: list[str] = []


class MeOut(UserOut):
    tenant_name: str | None = None


class RoleIn(BaseModel):
    role: str = Field(min_length=1, max_length=30)


class OrganizationIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    org_type: str = Field(default="customer", max_length=32)


class OrganizationOut(OrganizationIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    is_active: bool
    created_at: datetime


class ContactIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    organization_id: uuid.UUID | None = None


class ContactOut(ContactIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID | None
    is_active: bool
    created_at: datetime


class TicketCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1)
    priority: str = Field(default="P3", pattern="^P[1-4]$")
    category: str | None = Field(default=None, max_length=50)
    ticket_type: str = Field(default="INCIDENT", max_length=32)
    source: str = Field(default="WEB", max_length=32)
    organization_id: uuid.UUID | None = None
    requester_contact_id: uuid.UUID | None = None


class TicketTransition(BaseModel):
    to_status: str = Field(min_length=1, max_length=30)
    version: int | None = None


class TicketStatus(BaseModel):
    status: str = Field(pattern="^(NEW|OPEN|IN_PROGRESS|WAITING_FOR_CUSTOMER|WAITING_FOR_INTERNAL|ON_HOLD|RESOLVED|CLOSED|CANCELLED)$")


class Assignment(BaseModel):
    assignee_id: uuid.UUID | None = None
    team_id: uuid.UUID | None = None
    queue_id: uuid.UUID | None = None


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    ticket_number: str
    title: str
    description: str
    status: str
    priority: str
    ticket_type: str = "INCIDENT"
    source: str = "WEB"
    category: str | None
    category_id: uuid.UUID | None = None
    customer_id: uuid.UUID | None
    requester_contact_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None
    assignee_id: uuid.UUID | None
    team_id: uuid.UUID | None = None
    queue_id: uuid.UUID | None = None
    version: int = 1
    created_at: datetime
    updated_at: datetime | None = None
    first_response_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    allowed_transitions: list[str] = []


class CommentCreate(BaseModel):
    body: str = Field(min_length=1)
    is_internal: bool = False


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    ticket_id: uuid.UUID
    author_id: uuid.UUID
    body: str
    is_internal: bool
    created_at: datetime


class SLAPolicyIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    priority: str = Field(pattern="^P[1-4]$")
    first_response_minutes: int = Field(gt=0)
    resolution_hours: int = Field(gt=0)
    is_active: bool = True


class SLAPolicyOut(SLAPolicyIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class TicketSLAOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    ticket_id: uuid.UUID
    policy_id: uuid.UUID
    first_response_due_at: datetime | None
    resolution_due_at: datetime | None
    first_responded_at: datetime | None
    resolved_at: datetime | None
    breached_at: datetime | None
    paused_at: datetime | None = None
    status: str


class TeamIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class TeamOut(TeamIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    is_active: bool


class QueueIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    team_id: uuid.UUID | None = None
    assignment_mode: str = Field(default="manual", max_length=32)


class QueueOut(QueueIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    is_active: bool


class TagIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class TagOut(TagIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID


class SavedViewIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    filters: dict = Field(default_factory=dict)
    is_shared: bool = False


class SavedViewOut(SavedViewIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID | None


class MacroIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    reply_body: str | None = None
    actions: list = Field(default_factory=list)


class MacroOut(MacroIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    is_active: bool


class AutomationRuleIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    trigger_event: str
    conditions: dict = Field(default_factory=dict)
    actions: list = Field(default_factory=list)
    sort_order: int = 0
    is_active: bool = True


class AutomationRuleOut(AutomationRuleIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID


class KBArticleIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1)
    visibility: str = Field(default="internal")
    status: str = Field(default="draft")


class KBArticleOut(KBArticleIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    version: int
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class CSATIn(BaseModel):
    score: int = Field(ge=1, le=5)
    comment: str | None = None


class CSATOut(CSATIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    ticket_id: uuid.UUID
    created_at: datetime


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    body: str
    is_read: bool
    created_at: datetime


class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    ticket_id: uuid.UUID
    filename: str
    mime_type: str
    size_bytes: int
    status: str
    created_at: datetime


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    actor_id: uuid.UUID | None
    actor_name: str | None = None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    entity_name: str | None = None
    old_values: dict
    new_values: dict
    correlation_id: str | None
    created_at: datetime


class BulkTicketAction(BaseModel):
    ticket_ids: list[uuid.UUID] = Field(min_length=1)
    action: str
    payload: dict = Field(default_factory=dict)


class ReportSummary(BaseModel):
    open_tickets: int
    resolved_tickets: int
    sla_breached: int
    unassigned: int


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
