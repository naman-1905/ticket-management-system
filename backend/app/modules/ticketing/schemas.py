from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
class TicketCreate(BaseModel): title: str = Field(max_length=300); description: str; priority: str = "P3"; category: str | None = None
class TicketStatus(BaseModel): status: str
class Assignment(BaseModel): assignee_id: UUID
class CommentCreate(BaseModel): body: str; is_internal: bool = False
class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; ticket_number: str; title: str; description: str; status: str; priority: str; category: str | None; customer_id: UUID; assignee_id: UUID | None; created_at: datetime
class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; ticket_id: UUID; author_id: UUID; body: str; is_internal: bool; created_at: datetime
