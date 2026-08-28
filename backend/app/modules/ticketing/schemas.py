from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
class TicketCreate(BaseModel): title: str = Field(min_length=1, max_length=300); description: str = Field(min_length=1); priority: Literal["P1", "P2", "P3", "P4"] = "P3"; category: str | None = Field(default=None, max_length=50)
class TicketStatus(BaseModel): status: Literal["OPEN", "IN_PROGRESS", "ON_HOLD", "RESOLVED", "CLOSED"]
class Assignment(BaseModel): assignee_id: UUID
class CommentCreate(BaseModel): body: str; is_internal: bool = False
class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; ticket_number: str; title: str; description: str; status: str; priority: str; category: str | None; customer_id: UUID; assignee_id: UUID | None; created_at: datetime
class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; ticket_id: UUID; author_id: UUID; body: str; is_internal: bool; created_at: datetime
