"""Transactional-outbox event service (Track O).

``emit_event`` writes an :class:`~app.models.OutboxEvent` row inside the caller's
transaction (the same boundary as the state mutation it describes), so an event is
persisted if and only if the business change commits. ``relay_events`` is run by the
worker loop: it polls unpublished events, dispatches each to its registered
consumers, tracks per-consumer delivery in :class:`~app.models.EventDelivery`, and
retries failures with exponential backoff until they dead-letter.

At-least-once guarantee: an event stays pollable (``published_at IS NULL``) until
every consumer delivery has reached a terminal state (``delivered`` or
``dead_letter``). Because each handler's side effects and its delivery-status update
commit in the same transaction, a successfully-handled event is applied exactly once.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import raise_api_error
from ..domain.events import get_event_type, missing_payload_keys
from ..models import OutboxEvent, EventDelivery
from .audit import audit_log

logger = logging.getLogger(__name__)

# Relay tuning. Kept as module constants so Phase 1 stays self-contained; promote to
# settings if operational tuning (per-tenant batch size / retry budget) is needed.
MAX_DELIVERY_ATTEMPTS = 5
RELAY_BATCH_SIZE = 20
_BACKOFF_BASE_SECONDS = 30
_BACKOFF_CAP_SECONDS = 900


def backoff_seconds(attempts: int) -> int:
    """Exponential backoff (base * 2^(attempts-1)) capped at ``_BACKOFF_CAP_SECONDS``."""
    if attempts <= 0:
        return _BACKOFF_BASE_SECONDS
    seconds = _BACKOFF_BASE_SECONDS * (2 ** (attempts - 1))
    return min(seconds, _BACKOFF_CAP_SECONDS)


def event_fully_published(deliveries) -> bool:
    """True once every delivery is terminal (delivered/dead_letter).

    While any delivery is still ``pending`` or ``failed`` (waiting to retry), the
    owning event must remain pollable so the relay revisits it.
    """
    for delivery in deliveries:
        if delivery.status in ("pending", "failed"):
            return False
    return True


# --- Consumer registry (in code, not DB) -------------------------------------
# Maps event_type -> list of (consumer_name, handler). Handlers are async and take
# (db, outbox_event); they must be idempotent on outbox_event.id because delivery is
# at-least-once. Registration happens in services.event_consumers (imported by the
# worker) so this module has no dependency on specific consumers.
CONSUMERS: dict[str, list[tuple[str, object]]] = {}


def register_consumer(event_type: str, name: str, handler):
    """Register a consumer for ``event_type`` under ``name``.

    Idempotent per ``(event_type, name)``: re-registering the same consumer name is a
    no-op, so an accidental double-registration (module re-import, in-process worker
    restart) cannot create two deliveries sharing one ``(event_id, consumer_name)``
    and trip the unique constraint on ``event_deliveries``.
    """
    existing = CONSUMERS.setdefault(event_type, [])
    if any(consumer_name == name for consumer_name, _ in existing):
        return
    existing.append((name, handler))


def consumers_for(event_type: str) -> list[tuple[str, object]]:
    return CONSUMERS.get(event_type, [])


# --- Emit ---------------------------------------------------------------------
async def emit_event(
    db: AsyncSession,
    tenant_id: uuid.UUID | None,
    event_type: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    payload: dict,
) -> OutboxEvent:
    """Write a domain event to the outbox in the caller's transaction.

    Validates the event type is registered and the payload carries its required keys,
    then adds (and flushes for an id) an :class:`OutboxEvent` with ``published_at``
    unset. The relay publishes it later. Returns the flushed row.
    """
    et = get_event_type(event_type)
    if et is None:
        raise_api_error(500, "UNKNOWN_EVENT_TYPE", f"Unknown event type: {event_type}")
    missing = missing_payload_keys(event_type, payload)
    if missing:
        raise_api_error(
            500, "INVALID_EVENT_PAYLOAD", f"Missing keys for {event_type}: {missing}"
        )
    event = OutboxEvent(
        tenant_id=tenant_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        payload_json=payload or {},
        schema_version=et.schema_version,
    )
    db.add(event)
    await db.flush()
    return event


# --- Relay --------------------------------------------------------------------
async def _get_or_create_delivery(
    db: AsyncSession, event: OutboxEvent, consumer_name: str
) -> EventDelivery:
    delivery = (
        await db.execute(
            select(EventDelivery).where(
                EventDelivery.event_id == event.id,
                EventDelivery.consumer_name == consumer_name,
            )
        )
    ).scalar_one_or_none()
    if delivery is None:
        delivery = EventDelivery(
            event_id=event.id, consumer_name=consumer_name, status="pending"
        )
        db.add(delivery)
        await db.flush()
    return delivery


async def relay_events(db: AsyncSession, batch_size: int = RELAY_BATCH_SIZE) -> int:
    """Poll unpublished outbox events and dispatch them to registered consumers.

    Runs inside the worker's single committed transaction (like ``process_jobs``).
    Returns the number of events fully published this pass. A consumer that keeps
    failing is retried with backoff and dead-lettered after ``MAX_DELIVERY_ATTEMPTS``.
    """
    now = datetime.now(timezone.utc)
    events = (
        await db.execute(
            select(OutboxEvent)
            .where(OutboxEvent.published_at.is_(None))
            .order_by(OutboxEvent.created_at, OutboxEvent.id)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
    ).scalars().all()

    published = 0
    for event in events:
        consumers = consumers_for(event.event_type)
        deliveries = []
        for consumer_name, handler in consumers:
            delivery = await _get_or_create_delivery(db, event, consumer_name)
            deliveries.append(delivery)
            if delivery.status in ("delivered", "dead_letter"):
                continue  # terminal
            if delivery.next_attempt_at and delivery.next_attempt_at > now:
                continue  # still inside the backoff window
            try:
                await handler(db, event)
                delivery.status = "delivered"
                delivery.attempts += 1
                delivery.last_error = None
            except Exception as exc:  # noqa: BLE001 - one bad consumer must not kill the relay
                delivery.attempts += 1
                delivery.last_error = str(exc)[:2000]
                if delivery.attempts >= MAX_DELIVERY_ATTEMPTS:
                    delivery.status = "dead_letter"
                else:
                    delivery.status = "failed"
                    delivery.next_attempt_at = now + timedelta(
                        seconds=backoff_seconds(delivery.attempts)
                    )
        if event_fully_published(deliveries):
            event.published_at = now
            published += 1
    return published


# --- Query / admin helpers ----------------------------------------------------
async def list_events(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
    page: int = 1,
    size: int = 20,
):
    q = select(OutboxEvent).where(OutboxEvent.tenant_id == tenant_id)
    if entity_type:
        q = q.where(OutboxEvent.entity_type == entity_type)
    if entity_id:
        q = q.where(OutboxEvent.entity_id == entity_id)
    if from_dt:
        q = q.where(OutboxEvent.created_at >= from_dt)
    if to_dt:
        q = q.where(OutboxEvent.created_at <= to_dt)
    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    rows = (
        await db.execute(
            q.order_by(OutboxEvent.created_at.desc(), OutboxEvent.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
    ).scalars().all()
    return rows, total or 0


async def list_dead_letters(
    db: AsyncSession, tenant_id: uuid.UUID, *, page: int = 1, size: int = 20
):
    base = (
        select(EventDelivery, OutboxEvent)
        .join(OutboxEvent, OutboxEvent.id == EventDelivery.event_id)
        .where(EventDelivery.status == "dead_letter")
        .where(OutboxEvent.tenant_id == tenant_id)
    )
    count_q = (
        select(func.count())
        .select_from(EventDelivery)
        .join(OutboxEvent, OutboxEvent.id == EventDelivery.event_id)
        .where(EventDelivery.status == "dead_letter")
        .where(OutboxEvent.tenant_id == tenant_id)
    )
    total = await db.scalar(count_q)
    rows = (
        await db.execute(
            base.order_by(EventDelivery.updated_at.desc()).offset((page - 1) * size).limit(size)
        )
    ).all()
    return rows, total or 0


async def retry_dead_letter(db: AsyncSession, user, delivery_id: uuid.UUID):
    """Reset a dead-lettered delivery (and its event) so the relay redelivers it.

    Audits who retried which event/consumer. Returns the (delivery, event) pair.
    """
    delivery = (
        await db.execute(select(EventDelivery).where(EventDelivery.id == delivery_id))
    ).scalar_one_or_none()
    if not delivery:
        raise_api_error(404, "NOT_FOUND", "Dead-lettered delivery not found")
    event = (
        await db.execute(select(OutboxEvent).where(OutboxEvent.id == delivery.event_id))
    ).scalar_one_or_none()
    if not event or event.tenant_id != user.tenant_id:
        raise_api_error(404, "NOT_FOUND", "Dead-lettered delivery not found")
    delivery.status = "pending"
    delivery.attempts = 0
    delivery.last_error = None
    delivery.next_attempt_at = None
    event.published_at = None  # make the event pollable again
    await audit_log(
        db,
        user,
        "event.dead_letter_retried",
        "event_delivery",
        delivery.id,
        new_values={"event_id": str(event.id), "consumer": delivery.consumer_name},
    )
    return delivery, event
