import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
class Notification(Base):
    __tablename__="notifications"
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4); recipient_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("users.id")); ticket_id: Mapped[uuid.UUID|None]=mapped_column(ForeignKey("tickets.id"),nullable=True); template_key: Mapped[str]=mapped_column(String(50)); channel: Mapped[str]=mapped_column(String(20),default="EMAIL"); subject: Mapped[str]=mapped_column(Text); body: Mapped[str]=mapped_column(Text); status: Mapped[str]=mapped_column(String(20),default="PENDING"); sent_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
