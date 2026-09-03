"""Built-in event consumers (Track O).

Importing this module registers concrete consumers against the registry in
``services.events``. The worker imports it at startup so the relay has handlers to
dispatch to. Consumers are idempotent on ``outbox_event.id``: each one guards its
side effect with a lookup keyed on the event id, so a redelivery (at-least-once)
never duplicates the effect.

Currently registered:
  * ticket.status_changed -> "ticket_status_notify" : in-app notification to the
    ticket's assignee (or creator), created exactly once per event.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Notification, Ticket
from .events import register_consumer


async def _notify_on_status_change(db: AsyncSession, event) -> None:
    payload = event.payload_json or {}
    ticket_id = payload.get("ticket_id")
    if not ticket_id:
        return
    ticket = (
        await db.execute(select(Ticket).where(Ticket.id == uuid.UUID(str(ticket_id))))
    ).scalar_one_or_none()
    if ticket is None:
        return

    recipient_id = ticket.assignee_id or ticket.created_by
    if recipient_id is None:
        return

    # Idempotency guard: skip if a notification for this event already exists.
    existing = (
        await db.execute(
            select(Notification).where(Notification.extra_data["event_id"].as_string() == str(event.id))
        )
    ).scalars().first()
    if existing is not None:
        return

    from_status = payload.get("from_status")
    to_status = payload.get("to_status")
    db.add(
        Notification(
            tenant_id=event.tenant_id,
            user_id=recipient_id,
            channel="in_app",
            title=f"Ticket {ticket.ticket_number} status changed",
            body=f"Status moved from {from_status} to {to_status}.",
            extra_data={
                "event_id": str(event.id),
                "ticket_id": str(ticket.id),
                "ticket_number": ticket.ticket_number,
                "from_status": from_status,
                "to_status": to_status,
            },
        )
    )


def register_builtin_consumers() -> None:
    """Register all built-in consumers. Idempotent per process (called once at startup)."""
    register_consumer("ticket.status_changed", "ticket_status_notify", _notify_on_status_change)
