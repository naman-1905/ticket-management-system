import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import CSATRating, Ticket
from ..schemas import CSATIn, CSATOut
from ..deps import current_user
from ..services.tickets import get_ticket_for_user
from ..utils import err

router = APIRouter()


@router.post("/tickets/{ticket_id}", response_model=CSATOut, status_code=201)
async def submit_csat(
    ticket_id: uuid.UUID,
    body: CSATIn,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await get_ticket_for_user(db, ticket_id, user)
    if ticket.status not in ("RESOLVED", "CLOSED"):
        err(400, "VALIDATION_ERROR", "CSAT only available for resolved tickets")
    existing = (
        await db.execute(select(CSATRating).where(CSATRating.ticket_id == ticket.id))
    ).scalar_one_or_none()
    if existing:
        err(409, "CONFLICT", "CSAT already submitted")
    rating = CSATRating(
        tenant_id=user.tenant_id,
        ticket_id=ticket.id,
        contact_id=ticket.requester_contact_id,
        score=body.score,
        comment=body.comment,
    )
    db.add(rating)
    await db.commit()
    await db.refresh(rating)
    return rating
