import hashlib
import secrets
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import raise_api_error
from ..domain.ticket_lifecycle import PAUSE_STATUSES, can_transition, get_allowed_transitions
from ..models import (
    Ticket,
    Comment,
    Contact,
    SLAPolicy,
    SLAPolicyVersion,
    TicketSLA,
    SLAEvent,
    Tag,
    TicketTag,
    User,
)
from ..services.tenancy import user_has_permission
from .audit import audit_log
from .events import emit_event
from .idempotency import get_idempotent, save_idempotent


async def next_ticket_number(db: AsyncSession, tenant_id: uuid.UUID) -> str:
    count = await db.scalar(
        select(func.count()).select_from(Ticket).where(Ticket.tenant_id == tenant_id)
    )
    return f"TCK-{int(count or 0) + 1:06d}"


def build_search_vector(ticket: Ticket) -> str:
    return f"{ticket.ticket_number} {ticket.title} {ticket.description}".lower()


async def attach_sla(db: AsyncSession, ticket: Ticket):
    policy = (
        await db.execute(
            select(SLAPolicy).where(
                SLAPolicy.tenant_id == ticket.tenant_id,
                SLAPolicy.priority == ticket.priority,
                SLAPolicy.is_active == True,  # noqa: E712
            ).order_by(SLAPolicy.created_at)
        )
    ).scalars().first()
    if not policy:
        return
    version = (
        await db.execute(
            select(SLAPolicyVersion)
            .where(SLAPolicyVersion.policy_id == policy.id)
            .order_by(SLAPolicyVersion.version.desc())
        )
    ).scalars().first()
    created = ticket.created_at or datetime.now(timezone.utc)
    fr_min = version.first_response_minutes if version else policy.first_response_minutes
    res_hrs = version.resolution_hours if version else policy.resolution_hours
    sla = TicketSLA(
        tenant_id=ticket.tenant_id,
        ticket_id=ticket.id,
        policy_id=policy.id,
        policy_version_id=version.id if version else None,
        first_response_due_at=created + timedelta(minutes=fr_min),
        resolution_due_at=created + timedelta(hours=res_hrs),
        status="ACTIVE",
    )
    db.add(sla)
    await db.flush()
    db.add(
        SLAEvent(
            tenant_id=ticket.tenant_id,
            ticket_sla_id=sla.id,
            event_type="sla_started",
            details={"policy_id": str(policy.id)},
        )
    )


async def get_ticket_for_user(db: AsyncSession, ticket_id: uuid.UUID, user: User) -> Ticket:
    ticket = (
        await db.execute(
            select(Ticket).where(Ticket.id == ticket_id, Ticket.tenant_id == user.tenant_id)
        )
    ).scalar_one_or_none()
    if not ticket:
        raise_api_error(404, "NOT_FOUND", "Ticket not found")
    if await user_has_permission(db, user, "ticket.view"):
        return ticket
    if await user_has_permission(db, user, "ticket.view_own"):
        if ticket.customer_id == user.id or ticket.created_by == user.id:
            return ticket
        contact = (
            await db.execute(select(Contact).where(Contact.user_id == user.id, Contact.tenant_id == user.tenant_id))
        ).scalar_one_or_none()
        if contact and ticket.requester_contact_id == contact.id:
            return ticket
    raise_api_error(404, "NOT_FOUND", "Ticket not found")


async def create_ticket(
    db: AsyncSession,
    user: User,
    *,
    title: str,
    description: str,
    priority: str = "P3",
    category: str | None = None,
    ticket_type: str = "INCIDENT",
    source: str = "WEB",
    organization_id: uuid.UUID | None = None,
    requester_contact_id: uuid.UUID | None = None,
    due_at: datetime | None = None,
    project_id: uuid.UUID | None = None,
    idempotency_key: str | None = None,
) -> Ticket:
    if not await user_has_permission(db, user, "ticket.create"):
        raise_api_error(403, "FORBIDDEN", "Insufficient permissions")
    endpoint = "POST:/tickets"
    cached = await get_idempotent(db, user, endpoint, idempotency_key)
    if cached:
        return cached
    contact = None
    if requester_contact_id:
        contact = (
            await db.execute(
                select(Contact).where(
                    Contact.id == requester_contact_id,
                    Contact.tenant_id == user.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not contact:
            raise_api_error(404, "NOT_FOUND", "Contact not found")
    else:
        contact = (
            await db.execute(select(Contact).where(Contact.user_id == user.id, Contact.tenant_id == user.tenant_id))
        ).scalar_one_or_none()
    ticket = Ticket(
        tenant_id=user.tenant_id,
        ticket_number=await next_ticket_number(db, user.tenant_id),
        title=title,
        description=description,
        status="NEW",
        priority=priority,
        category=category,
        ticket_type=ticket_type,
        source=source,
        customer_id=user.id if user.user_type == "customer" else (contact.user_id if contact and contact.user_id else user.id),
        requester_contact_id=contact.id if contact else None,
        organization_id=organization_id or (contact.organization_id if contact else None),
        project_id=project_id,
        due_at=due_at,
        created_by=user.id,
    )
    ticket.search_vector = build_search_vector(ticket)
    db.add(ticket)
    await db.flush()
    await attach_sla(db, ticket)
    await audit_log(db, user, "ticket.created", "ticket", ticket.id, new_values={"ticket_number": ticket.ticket_number})
    await emit_event(
        db,
        ticket.tenant_id,
        "ticket.created",
        "ticket",
        ticket.id,
        {
            "ticket_id": str(ticket.id),
            "ticket_number": ticket.ticket_number,
            "status": ticket.status,
            "priority": ticket.priority,
        },
    )
    await save_idempotent(db, user, endpoint, idempotency_key, 201, ticket_to_dict(ticket))
    return ticket


def _serialize_value(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


async def update_ticket(
    db: AsyncSession,
    user: User,
    ticket: Ticket,
    *,
    changes: dict,
    request_id: str | None = None,
) -> Ticket:
    """Apply a partial set of metadata fields to a ticket.

    `changes` is the result of `TicketUpdate.model_dump(exclude_unset=True)`, so a key
    that is present but `None` means "clear this field" (e.g. remove the deadline).
    """
    keys = [k for k in changes if k in ("title", "description", "priority", "category", "project_id", "due_at")]
    if not keys:
        return ticket
    old_values = {k: _serialize_value(getattr(ticket, k)) for k in keys}
    for k in keys:
        setattr(ticket, k, changes[k])
    if "title" in keys or "description" in keys:
        ticket.search_vector = build_search_vector(ticket)
    new_values = {k: _serialize_value(changes[k]) for k in keys}
    ticket.version += 1
    ticket.updated_at = datetime.now(timezone.utc)
    await audit_log(
        db, user, "ticket.updated", "ticket", ticket.id,
        old_values=old_values, new_values=new_values, correlation_id=request_id,
    )
    await emit_event(
        db, ticket.tenant_id, "ticket.updated", "ticket", ticket.id,
        {"ticket_id": str(ticket.id), "fields": keys},
    )
    return ticket


async def transition_ticket(
    db: AsyncSession,
    user: User,
    ticket: Ticket,
    to_status: str,
    *,
    request_id: str | None = None,
) -> Ticket:
    if not await user_has_permission(db, user, "ticket.transition"):
        if not (await user_has_permission(db, user, "ticket.view_own") and can_transition(user.role, ticket.status, to_status)):
            raise_api_error(403, "FORBIDDEN", "Insufficient permissions")
    elif not can_transition(user.role, ticket.status, to_status):
        raise_api_error(403, "FORBIDDEN", f"Invalid transition from {ticket.status} to {to_status}")
    old_status = ticket.status
    ticket.status = to_status
    ticket.version += 1
    ticket.updated_at = datetime.now(timezone.utc)
    now = datetime.now(timezone.utc)
    if to_status == "RESOLVED":
        ticket.resolved_at = now
    if to_status == "CLOSED":
        ticket.closed_at = now
    if to_status == "OPEN" and old_status in ("RESOLVED", "CLOSED"):
        ticket.resolved_at = None
        ticket.closed_at = None
    sla = (
        await db.execute(select(TicketSLA).where(TicketSLA.ticket_id == ticket.id))
    ).scalar_one_or_none()
    if sla:
        if to_status in PAUSE_STATUSES and not sla.paused_at:
            sla.paused_at = now
            db.add(SLAEvent(tenant_id=ticket.tenant_id, ticket_sla_id=sla.id, event_type="sla_paused", details={}))
        elif to_status not in PAUSE_STATUSES and sla.paused_at:
            paused_duration = now - sla.paused_at
            if sla.first_response_due_at:
                sla.first_response_due_at += paused_duration
            if sla.resolution_due_at:
                sla.resolution_due_at += paused_duration
            sla.paused_at = None
            db.add(SLAEvent(tenant_id=ticket.tenant_id, ticket_sla_id=sla.id, event_type="sla_resumed", details={}))
        if to_status == "RESOLVED":
            sla.resolved_at = now
            sla.status = "MET" if not sla.breached_at else "BREACHED"
    await audit_log(
        db,
        user,
        "ticket.status_changed",
        "ticket",
        ticket.id,
        old_values={"status": old_status},
        new_values={"status": to_status},
        correlation_id=request_id,
    )
    await emit_event(
        db,
        ticket.tenant_id,
        "ticket.status_changed",
        "ticket",
        ticket.id,
        {
            "ticket_id": str(ticket.id),
            "ticket_number": ticket.ticket_number,
            "from_status": old_status,
            "to_status": to_status,
        },
    )
    return ticket


async def add_comment(
    db: AsyncSession,
    user: User,
    ticket: Ticket,
    body: str,
    is_internal: bool = False,
    idempotency_key: str | None = None,
) -> Comment:
    if is_internal:
        if not await user_has_permission(db, user, "comment.internal.write"):
            raise_api_error(403, "FORBIDDEN", "Cannot create internal notes")
    else:
        if not await user_has_permission(db, user, "comment.public.write"):
            raise_api_error(403, "FORBIDDEN", "Cannot add comments")
    endpoint = f"POST:/tickets/{ticket.id}/comments"
    cached = await get_idempotent(db, user, endpoint, idempotency_key)
    if cached:
        return cached
    comment = Comment(
        tenant_id=ticket.tenant_id,
        ticket_id=ticket.id,
        author_id=user.id,
        body=body,
        is_internal=is_internal,
    )
    db.add(comment)
    await db.flush()
    if not is_internal:
        now = datetime.now(timezone.utc)
        if not ticket.first_response_at:
            ticket.first_response_at = now
        sla = (
            await db.execute(select(TicketSLA).where(TicketSLA.ticket_id == ticket.id))
        ).scalar_one_or_none()
        if sla and not sla.first_responded_at:
            sla.first_responded_at = now
            if sla.first_response_due_at and now <= sla.first_response_due_at:
                db.add(SLAEvent(tenant_id=ticket.tenant_id, ticket_sla_id=sla.id, event_type="first_response_met", details={}))
    ticket.search_vector = build_search_vector(ticket) + " " + body.lower()
    ticket.updated_at = datetime.now(timezone.utc)
    await audit_log(db, user, "comment.added", "comment", comment.id, new_values={"ticket_id": str(ticket.id)})
    payload = {
        "id": str(comment.id),
        "ticket_id": str(comment.ticket_id),
        "author_id": str(comment.author_id),
        "body": comment.body,
        "is_internal": comment.is_internal,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }
    await save_idempotent(db, user, endpoint, idempotency_key, 201, payload)
    return comment


def ticket_to_dict(ticket: Ticket, allowed: list[str] | None = None) -> dict:
    return {
        "id": str(ticket.id),
        "tenant_id": str(ticket.tenant_id),
        "ticket_number": ticket.ticket_number,
        "title": ticket.title,
        "description": ticket.description,
        "status": ticket.status,
        "priority": ticket.priority,
        "ticket_type": ticket.ticket_type,
        "source": ticket.source,
        "category": ticket.category,
        "category_id": str(ticket.category_id) if ticket.category_id else None,
        "customer_id": str(ticket.customer_id) if ticket.customer_id else None,
        "requester_contact_id": str(ticket.requester_contact_id) if ticket.requester_contact_id else None,
        "organization_id": str(ticket.organization_id) if ticket.organization_id else None,
        "assignee_id": str(ticket.assignee_id) if ticket.assignee_id else None,
        "team_id": str(ticket.team_id) if ticket.team_id else None,
        "queue_id": str(ticket.queue_id) if ticket.queue_id else None,
        "version": ticket.version,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
        "first_response_at": ticket.first_response_at.isoformat() if ticket.first_response_at else None,
        "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
        "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
        "allowed_transitions": allowed or [],
    }
