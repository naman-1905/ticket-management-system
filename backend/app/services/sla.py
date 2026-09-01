from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import TicketSLA, SLAEvent, Notification, User, Ticket


async def process_sla_breaches(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    processed = 0
    rows = (
        await db.execute(
            select(TicketSLA).where(
                TicketSLA.status == "ACTIVE",
                TicketSLA.breached_at.is_(None),
            )
        )
    ).scalars().all()
    for sla in rows:
        breached = False
        if sla.first_response_due_at and not sla.first_responded_at and sla.first_response_due_at < now:
            breached = True
            db.add(
                SLAEvent(
                    tenant_id=sla.tenant_id,
                    ticket_sla_id=sla.id,
                    event_type="first_response_breached",
                    details={},
                )
            )
        if sla.resolution_due_at and not sla.resolved_at and sla.resolution_due_at < now:
            breached = True
            db.add(
                SLAEvent(
                    tenant_id=sla.tenant_id,
                    ticket_sla_id=sla.id,
                    event_type="resolution_breached",
                    details={},
                )
            )
        if breached:
            sla.breached_at = now
            sla.status = "BREACHED"
            ticket = await db.get(Ticket, sla.ticket_id)
            if ticket and ticket.assignee_id:
                db.add(
                    Notification(
                        tenant_id=sla.tenant_id,
                        user_id=ticket.assignee_id,
                        channel="in_app",
                        title="SLA Breached",
                        body=f"Ticket {ticket.ticket_number} has breached SLA.",
                        extra_data={"ticket_id": str(ticket.id)},
                    )
                )
            processed += 1
    return processed
