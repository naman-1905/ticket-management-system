import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
class SLAPolicy(Base):
    __tablename__="sla_policies"
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4); name: Mapped[str]=mapped_column(String(100),unique=True); priority: Mapped[str]=mapped_column(String(5)); first_response_minutes: Mapped[int]=mapped_column(Integer); resolution_hours: Mapped[int]=mapped_column(Integer); is_active: Mapped[bool]=mapped_column(Boolean,default=True); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now()); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now())
class TicketSLA(Base):
    __tablename__="ticket_sla"
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4); ticket_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("tickets.id"),unique=True); policy_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("sla_policies.id")); first_response_due_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True); resolution_due_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True); first_responded_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True); resolved_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True); breached_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True); status: Mapped[str]=mapped_column(String(20),default="ACTIVE")
