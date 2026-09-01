import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AuditLog, User


async def audit_log(
    db: AsyncSession,
    user: User | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    old_values: dict | None = None,
    new_values: dict | None = None,
    correlation_id: str | None = None,
):
    db.add(
        AuditLog(
            tenant_id=user.tenant_id if user else None,
            actor_id=user.id if user else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values or {},
            new_values=new_values or {},
            correlation_id=correlation_id,
        )
    )
