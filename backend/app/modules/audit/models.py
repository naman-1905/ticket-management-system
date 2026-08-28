import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
class AuditLog(Base):
    __tablename__="audit_logs"
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4); actor_id: Mapped[uuid.UUID|None]=mapped_column(ForeignKey("users.id"),nullable=True); action: Mapped[str]=mapped_column(String(100)); entity_type: Mapped[str]=mapped_column(String(50)); entity_id: Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True),nullable=True); old_values: Mapped[dict|None]=mapped_column(JSON,nullable=True); new_values: Mapped[dict|None]=mapped_column(JSON,nullable=True); correlation_id: Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True),nullable=True); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
