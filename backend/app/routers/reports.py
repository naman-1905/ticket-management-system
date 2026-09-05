from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Ticket, TicketSLA
from ..schemas import ReportSummary, DashboardData, StatusCount, PriorityCount, TrendPoint
from ..deps import require_permissions

router = APIRouter()

OPEN_STATUSES = ["NEW", "OPEN", "IN_PROGRESS", "WAITING_FOR_CUSTOMER", "WAITING_FOR_INTERNAL", "ON_HOLD"]


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


@router.get("/tickets/dashboard", response_model=DashboardData)
async def ticket_dashboard(user=Depends(require_permissions("report.view")), db: AsyncSession = Depends(get_db)):
    tenant_id = user.tenant_id

    total = (
        await db.scalar(select(func.count()).select_from(Ticket).where(Ticket.tenant_id == tenant_id)) or 0
    )
    open_tickets = (
        await db.scalar(
            select(func.count()).select_from(Ticket).where(Ticket.tenant_id == tenant_id, Ticket.status.in_(OPEN_STATUSES))
        )
        or 0
    )
    resolved = (
        await db.scalar(
            select(func.count()).select_from(Ticket).where(Ticket.tenant_id == tenant_id, Ticket.status == "RESOLVED")
        )
        or 0
    )
    closed = (
        await db.scalar(
            select(func.count()).select_from(Ticket).where(Ticket.tenant_id == tenant_id, Ticket.status == "CLOSED")
        )
        or 0
    )
    unassigned = (
        await db.scalar(
            select(func.count()).select_from(Ticket).where(
                Ticket.tenant_id == tenant_id,
                Ticket.assignee_id.is_(None),
                Ticket.status.in_(OPEN_STATUSES),
            )
        )
        or 0
    )
    breached = (
        await db.scalar(
            select(func.count()).select_from(TicketSLA).where(
                TicketSLA.tenant_id == tenant_id,
                TicketSLA.status == "BREACHED",
            )
        )
        or 0
    )

    # Average time from creation to resolution (hours) across resolved tickets.
    avg_seconds = await db.scalar(
        select(func.avg(func.extract("epoch", Ticket.resolved_at - Ticket.created_at))).where(
            Ticket.tenant_id == tenant_id,
            Ticket.resolved_at.isnot(None),
        )
    )
    avg_resolution_hours = round(float(avg_seconds) / 3600.0, 1) if avg_seconds else None

    status_rows = (
        await db.execute(
            select(Ticket.status, func.count()).where(Ticket.tenant_id == tenant_id).group_by(Ticket.status)
        )
    ).all()
    by_status = [StatusCount(status=r[0], count=int(r[1])) for r in status_rows]

    priority_rows = (
        await db.execute(
            select(Ticket.priority, func.count()).where(Ticket.tenant_id == tenant_id).group_by(Ticket.priority)
        )
    ).all()
    by_priority = [PriorityCount(priority=r[0], count=int(r[1])) for r in priority_rows]

    # Daily created vs resolved counts over the trailing window (including today).
    days = 14
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=days - 1)

    created_rows = (
        await db.execute(
            select(func.date(Ticket.created_at), func.count())
            .where(Ticket.tenant_id == tenant_id, func.date(Ticket.created_at) >= start_date)
            .group_by(func.date(Ticket.created_at))
        )
    ).all()
    created_map = {str(d): int(c) for d, c in created_rows}

    resolved_rows = (
        await db.execute(
            select(func.date(Ticket.resolved_at), func.count())
            .where(Ticket.tenant_id == tenant_id, Ticket.resolved_at.isnot(None), func.date(Ticket.resolved_at) >= start_date)
            .group_by(func.date(Ticket.resolved_at))
        )
    ).all()
    resolved_map = {str(d): int(c) for d, c in resolved_rows}

    trend: list[TrendPoint] = []
    for i in range(days):
        ds = (start_date + timedelta(days=i)).isoformat()
        trend.append(TrendPoint(date=ds, created=created_map.get(ds, 0), resolved=resolved_map.get(ds, 0)))

    return DashboardData(
        total_tickets=int(total),
        open_tickets=int(open_tickets),
        resolved_tickets=int(resolved),
        closed_tickets=int(closed),
        unassigned=int(unassigned),
        sla_breached=int(breached),
        avg_resolution_hours=avg_resolution_hours,
        by_status=by_status,
        by_priority=by_priority,
        trend=trend,
    )
