from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Notification
from ..schemas import NotificationOut
from ..deps import current_user

router = APIRouter()


@router.get("", response_model=list[NotificationOut])
async def list_notifications(user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    return (
        await db.execute(
            select(Notification)
            .where(Notification.tenant_id == user.tenant_id, Notification.user_id == user.id)
            .order_by(Notification.created_at.desc())
            .limit(50)
        )
    ).scalars().all()


@router.post("/read-all", status_code=204)
async def mark_all_read(user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.tenant_id == user.tenant_id, Notification.is_read == False)  # noqa: E712
        .values(is_read=True)
    )
    await db.commit()
