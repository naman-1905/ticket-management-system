from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Ticket
from ..schemas import TicketOut, Page
from ..deps import current_user
from ..services.tenancy import user_has_permission
from ..routers.tickets import _ticket_out
from ..utils import err

router = APIRouter()


@router.get("/tickets", response_model=Page[TicketOut])
async def search_tickets(
    q: str = Query(min_length=1),
    page: int = 1,
    size: int = 20,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await user_has_permission(db, user, "ticket.view"):
        err(403, "FORBIDDEN", "Insufficient permissions")
    page = max(page, 1)
    size = min(max(size, 1), 100)
    like = f"%{q.lower()}%"
    query = select(Ticket).where(
        Ticket.tenant_id == user.tenant_id,
        or_(Ticket.search_vector.ilike(like), Ticket.ticket_number.ilike(like), Ticket.title.ilike(like)),
    )
    from sqlalchemy import func

    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    rows = (
        await db.execute(query.order_by(Ticket.created_at.desc()).offset((page - 1) * size).limit(size))
    ).scalars().all()
    return Page(items=[await _ticket_out(db, t, user) for t in rows], total=total or 0, page=page, size=size)
