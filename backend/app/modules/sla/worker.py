import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from app.db.database import SessionLocal
from app.modules.ticketing.models import Ticket
from .models import TicketSLA
from app.modules.ticketing.events import event_bus
async def sla_worker(stop_event: asyncio.Event, interval: int = 60):
    while not stop_event.is_set():
        try:
            async with SessionLocal() as db:
                now = datetime.now(timezone.utc)
                rows = (await db.execute(select(TicketSLA, Ticket).join(Ticket, Ticket.id == TicketSLA.ticket_id).where(TicketSLA.status == "ACTIVE", Ticket.status.not_in({"RESOLVED", "CLOSED"}), TicketSLA.resolution_due_at < now))).all()
                for sla, ticket in rows:
                    sla.status = "BREACHED"; sla.breached_at = now
                    await event_bus.publish("sla.breached", {"ticket_id": str(ticket.id), "breached_at": now.isoformat()})
                if rows: await db.commit()
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError: pass
        except asyncio.CancelledError: raise
        except Exception:
            await asyncio.sleep(min(interval, 5))
