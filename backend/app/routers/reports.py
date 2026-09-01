from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Ticket, TicketSLA
from ..schemas import ReportSummary
from ..deps import require_permissions

router = APIRouter()


@router.get("/tickets/summary", response_model=ReportSummary)
async def ticket_summary(user=Depends(require_permissions("report.view")), db: AsyncSession = Depends(get_db)):
    open_statuses = ["NEW", "OPEN", "IN_PROGRESS", "WAITING_FOR_CUSTOMER", "WAITING_FOR_INTERNAL", "ON_HOLD"]
    open_tickets = await db.scalar(
        select(func.count()).select_from(Ticket).where(Ticket.tenant_id == user.tenant_id, Ticket.status.in_(open_statuses))
    )
    resolved = await db.scalar(
        select(func.count()).select_from(Ticket).where(Ticket.tenant_id == user.tenant_id, Ticket.status == "RESOLVED")
    )
    unassigned = await db.scalar(
        select(func.count()).select_from(Ticket).where(
            Ticket.tenant_id == user.tenant_id,
            Ticket.assignee_id.is_(None),
            Ticket.status.in_(open_statuses),
        )
    )
    breached = await db.scalar(
        select(func.count()).select_from(TicketSLA).where(
            TicketSLA.tenant_id == user.tenant_id,
            TicketSLA.status == "BREACHED",
        )
    )
    return ReportSummary(
        open_tickets=open_tickets or 0,
        resolved_tickets=resolved or 0,
        sla_breached=breached or 0,
        unassigned=unassigned or 0,
    )
