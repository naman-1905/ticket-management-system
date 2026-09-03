import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..schemas import DeadLetterOut, EventOut, Page
from ..deps import require_permissions
from ..services.events import list_events, list_dead_letters, retry_dead_letter

router = APIRouter()


@router.get("/events", response_model=Page[EventOut])
async def events(
    page: int = 1,
    size: int = 20,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    from_: datetime | None = None,
    to: datetime | None = None,
    user=Depends(require_permissions("event.view")),
    db: AsyncSession = Depends(get_db),
):
    page = max(page, 1)
    size = min(max(size, 1), 100)
    rows, total = await list_events(
        db,
        user.tenant_id,
        entity_type=entity_type,
        entity_id=entity_id,
        from_dt=from_,
        to_dt=to,
        page=page,
        size=size,
    )
    return Page(items=[EventOut.model_validate(r) for r in rows], total=total, page=page, size=size)


@router.get("/events/dead-letter", response_model=Page[DeadLetterOut])
async def dead_letters(
    page: int = 1,
    size: int = 20,
    user=Depends(require_permissions("event.admin")),
    db: AsyncSession = Depends(get_db),
):
    page = max(page, 1)
    size = min(max(size, 1), 100)
    rows, total = await list_dead_letters(db, user.tenant_id, page=page, size=size)
    items = [
        DeadLetterOut(
            delivery_id=d.id,
            consumer_name=d.consumer_name,
            status=d.status,
            attempts=d.attempts,
            last_error=d.last_error,
            updated_at=d.updated_at,
            event_id=e.id,
            event_type=e.event_type,
            entity_type=e.entity_type,
            entity_id=e.entity_id,
            created_at=e.created_at,
        )
        for d, e in rows
    ]
    return Page(items=items, total=total, page=page, size=size)


@router.post("/events/dead-letter/{delivery_id}/retry")
async def dead_letter_retry(
    delivery_id: uuid.UUID,
    user=Depends(require_permissions("event.admin")),
    db: AsyncSession = Depends(get_db),
):
    delivery, event = await retry_dead_letter(db, user, delivery_id)
    return {
        "retried": True,
        "delivery_id": str(delivery.id),
        "event_id": str(event.id),
        "consumer": delivery.consumer_name,
    }
