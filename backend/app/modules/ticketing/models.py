import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
class Ticket(Base):
    __tablename__ = "tickets"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_number: Mapped[str] = mapped_column(String(20), unique=True, index=True); title: Mapped[str] = mapped_column(String(300)); description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="OPEN", index=True); priority: Mapped[str] = mapped_column(String(5), default="P3", index=True); category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id")); assignee_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True); created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id")); created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now()); updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (Index("ix_tickets_status_priority", "status", "priority"),)
class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4); ticket_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE")); author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id")); body: Mapped[str] = mapped_column(Text); is_internal: Mapped[bool] = mapped_column(Boolean, default=False); created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
