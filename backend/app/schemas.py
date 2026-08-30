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

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class RefreshIn(BaseModel):
    refresh_token: str

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    is_active: bool

class UserDBOut(UserOut):
    password_hash: str
    created_at: datetime

class RoleIn(BaseModel):
    role: str = Field(pattern="^(CUSTOMER|AGENT|ADMIN)$")

class TicketCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1)
    priority: str = Field(default="P3", pattern="^P[1-4]$")
    category: str | None = Field(default=None, max_length=50)

class TicketStatus(BaseModel):
    status: str = Field(pattern="^(OPEN|IN_PROGRESS|ON_HOLD|RESOLVED|CLOSED)$")

class Assignment(BaseModel):
    assignee_id: uuid.UUID

class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    ticket_number: str
    title: str
    description: str
    status: str
    priority: str
    category: str | None
    customer_id: uuid.UUID
    assignee_id: uuid.UUID | None
    created_at: datetime

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
    status: str

class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    actor_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    old_values: dict
    new_values: dict
    correlation_id: uuid.UUID | None
    created_at: datetime

T = TypeVar("T")
class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
