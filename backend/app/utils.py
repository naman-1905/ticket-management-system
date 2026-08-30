import uuid
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import AuditLog, IdempotencyRecord

def err(status_code, code, message, details=None):
    raise HTTPException(status_code=status_code, detail={"code": code, "message": message, "details": details or {}})

async def audit(db, actor_id, action, entity_type, entity_id, old_values=None, new_values=None):
    db.add(AuditLog(actor_id=actor_id, action=action, entity_type=entity_type, entity_id=entity_id,
                    old_values=old_values or {}, new_values=new_values or {}, correlation_id=uuid.uuid4()))

async def get_idempotent(db, user_id, endpoint, key):
    if not key:
        return None
    return (await db.execute(select(IdempotencyRecord).where(
        IdempotencyRecord.user_id == user_id, IdempotencyRecord.endpoint == endpoint, IdempotencyRecord.idem_key == key
    ))).scalar_one_or_none()

async def save_idempotent(db, user_id, endpoint, key, status_code, body):
    if key:
        db.add(IdempotencyRecord(user_id=user_id, endpoint=endpoint, idem_key=key, status_code=status_code, response_body=body))
