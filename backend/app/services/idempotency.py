import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import IdempotencyRecord, User


async def get_idempotent(db: AsyncSession, user: User, endpoint: str, key: str | None):
    if not key:
        return None
    record = (
        await db.execute(
            select(IdempotencyRecord).where(
                IdempotencyRecord.user_id == user.id,
                IdempotencyRecord.endpoint == endpoint,
                IdempotencyRecord.idem_key == key,
            )
        )
    ).scalar_one_or_none()
    return record.response_body if record else None


async def save_idempotent(
    db: AsyncSession,
    user: User,
    endpoint: str,
    key: str | None,
    status_code: int,
    response_body: dict,
):
    if not key:
        return
    db.add(
        IdempotencyRecord(
            tenant_id=user.tenant_id,
            user_id=user.id,
            endpoint=endpoint,
            idem_key=key,
            status_code=status_code,
            response_body=response_body,
        )
    )
