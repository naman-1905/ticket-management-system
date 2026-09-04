import uuid

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Ticket, Comment, User, Team, Queue
from ..schemas import (
    TicketCreate,
    TicketOut,
    TicketTransition,
    TicketStatus,
    Assignment,
    CommentCreate,
    CommentOut,
    Page,
    BulkTicketAction,
)
from ..deps import current_user, require_permissions
from ..domain.ticket_lifecycle import get_allowed_transitions
from ..services.tickets import (
    create_ticket,
    get_ticket_for_user,
    transition_ticket,
    add_comment,
    ticket_to_dict,
)
from ..services.tenancy import user_has_permission
from ..services.idempotency import get_idempotent
from ..utils import err

router = APIRouter()


async def _ticket_out(db: AsyncSession, ticket: Ticket, user: User) -> TicketOut:
  assignee_name = None
  if ticket.assignee_id:
    assignee_name = await db.scalar(select(User.full_name).where(User.id == ticket.assignee_id))
  return _ticket_out_sync(ticket, user, assignee_name)


def _ticket_out_sync(ticket: Ticket, user: User, assignee_name: str | None = None) -> TicketOut:
  allowed = get_allowed_transitions(user.role, ticket.status)
  return TicketOut(
      id=ticket.id,
      tenant_id=ticket.tenant_id,
      ticket_number=ticket.ticket_number,
      title=ticket.title,
      description=ticket.description,
      status=ticket.status,
      priority=ticket.priority,
      ticket_type=ticket.ticket_type,
      source=ticket.source,
      category=ticket.category,
      category_id=ticket.category_id,
      customer_id=ticket.customer_id,
      requester_contact_id=ticket.requester_contact_id,
      organization_id=ticket.organization_id,
      assignee_id=ticket.assignee_id,
      assignee_name=assignee_name,
      team_id=ticket.team_id,
      queue_id=ticket.queue_id,
      version=ticket.version,
      created_at=ticket.created_at,
      updated_at=ticket.updated_at,
      first_response_at=ticket.first_response_at,
      resolved_at=ticket.resolved_at,
      closed_at=ticket.closed_at,
      allowed_transitions=allowed,
  )


@router.post("", response_model=TicketOut, status_code=201)
async def create_ticket_endpoint(
    body: TicketCreate,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    cached = await get_idempotent(db, user, "POST:/tickets", idempotency_key)
    if cached:
        return cached
    ticket = await create_ticket(
        db,
        user,
        title=body.title,
        description=body.description,
        priority=body.priority,
        category=body.category,
        ticket_type=body.ticket_type,
        source=body.source,
        organization_id=body.organization_id,
        requester_contact_id=body.requester_contact_id,
        idempotency_key=idempotency_key,
    )
    await db.commit()
    await db.refresh(ticket)
    return await _ticket_out(db, ticket, user)


@router.get("", response_model=Page[TicketOut])
async def list_tickets(
    page: int = 1,
    size: int = 20,
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    assignee_id: uuid.UUID | None = None,
    q: str | None = None,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    page = max(page, 1)
    size = min(max(size, 1), 100)
    query = select(Ticket).where(Ticket.tenant_id == user.tenant_id)
    if not await user_has_permission(db, user, "ticket.view"):
        if await user_has_permission(db, user, "ticket.view_own"):
            query = query.where(or_(Ticket.customer_id == user.id, Ticket.created_by == user.id))
        else:
            err(403, "FORBIDDEN", "Insufficient permissions")
    if status:
        query = query.where(Ticket.status == status)
    if priority:
        query = query.where(Ticket.priority == priority)
    if category:
        query = query.where(Ticket.category == category)
    if assignee_id:
        query = query.where(Ticket.assignee_id == assignee_id)
    if q:
        like = f"%{q.lower()}%"
        query = query.where(
            or_(
                Ticket.search_vector.ilike(like),
                Ticket.ticket_number.ilike(like),
                Ticket.title.ilike(like),
            )
        )
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    rows = (
        await db.execute(query.order_by(Ticket.created_at.desc()).offset((page - 1) * size).limit(size))
    ).scalars().all()
    return Page(
        items=[await _ticket_out(db, t, user) for t in rows],
        total=total or 0, page=page, size=size,
    )


@router.get("/{ticket_id}", response_model=TicketOut)
async def get_one(ticket_id: uuid.UUID, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    ticket = await get_ticket_for_user(db, ticket_id, user)
    return await _ticket_out(db, ticket, user)


@router.post("/{ticket_id}/transitions", response_model=TicketOut)
async def transition(
    ticket_id: uuid.UUID,
    body: TicketTransition,
    request: Request,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await get_ticket_for_user(db, ticket_id, user)
    if body.version is not None and body.version != ticket.version:
        err(409, "CONFLICT", "Ticket was modified by another user")
    ticket = await transition_ticket(db, user, ticket, body.to_status, request_id=getattr(request.state, "request_id", None))
    await db.commit()
    await db.refresh(ticket)
    return await _ticket_out(db, ticket, user)


@router.patch("/{ticket_id}/status", response_model=TicketOut)
async def change_status_legacy(
    ticket_id: uuid.UUID,
    body: TicketStatus,
    request: Request,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await get_ticket_for_user(db, ticket_id, user)
    ticket = await transition_ticket(db, user, ticket, body.status, request_id=getattr(request.state, "request_id", None))
    await db.commit()
    await db.refresh(ticket)
    return await _ticket_out(db, ticket, user)


@router.post("/{ticket_id}/assign", response_model=TicketOut)
async def assign(
    ticket_id: uuid.UUID,
    body: Assignment,
    user=Depends(require_permissions("ticket.assign")),
    db: AsyncSession = Depends(get_db),
):
    ticket = await get_ticket_for_user(db, ticket_id, user)
    if body.assignee_id:
        assignee = (
            await db.execute(
                select(User).where(
                    User.id == body.assignee_id,
                    User.tenant_id == user.tenant_id,
                    User.is_active == True,  # noqa: E712
                    User.user_type == "staff",
                )
            )
        ).scalar_one_or_none()
        if not assignee:
            err(404, "NOT_FOUND", "Active agent not found")
        ticket.assignee_id = assignee.id
    if body.team_id:
        team = (
            await db.execute(select(Team).where(Team.id == body.team_id, Team.tenant_id == user.tenant_id))
        ).scalar_one_or_none()
        if not team:
            err(404, "NOT_FOUND", "Team not found")
        ticket.team_id = team.id
    if body.queue_id:
        queue = (
            await db.execute(select(Queue).where(Queue.id == body.queue_id, Queue.tenant_id == user.tenant_id))
        ).scalar_one_or_none()
        if not queue:
            err(404, "NOT_FOUND", "Queue not found")
        ticket.queue_id = queue.id
    ticket.version += 1
    await db.commit()
    await db.refresh(ticket)
    return await _ticket_out(db, ticket, user)


async def _comment_out(db: AsyncSession, comment: Comment) -> dict:
    """Serialize a comment with its author's display name."""
    author = await db.scalar(select(User.full_name).where(User.id == comment.author_id))
    return {
        "id": comment.id,
        "ticket_id": comment.ticket_id,
        "author_id": comment.author_id,
        "author_name": author,
        "body": comment.body,
        "is_internal": comment.is_internal,
        "created_at": comment.created_at,
    }


@router.get("/{ticket_id}/comments", response_model=list[CommentOut])
async def comments(ticket_id: uuid.UUID, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    ticket = await get_ticket_for_user(db, ticket_id, user)
    q = select(Comment).where(Comment.ticket_id == ticket.id, Comment.tenant_id == user.tenant_id).order_by(Comment.created_at)
    if not await user_has_permission(db, user, "comment.internal.read"):
        q = q.where(Comment.is_internal == False)  # noqa: E712
    rows = (await db.execute(q)).scalars().all()
    author_ids = {c.author_id for c in rows}
    names = {}
    if author_ids:
        pairs = (
            await db.execute(select(User.id, User.full_name).where(User.id.in_(author_ids)))
        ).all()
        names = {uid: name for uid, name in pairs}
    return [
        CommentOut(
            id=c.id, ticket_id=c.ticket_id, author_id=c.author_id,
            author_name=names.get(c.author_id), body=c.body,
            is_internal=c.is_internal, created_at=c.created_at,
        )
        for c in rows
    ]


@router.post("/{ticket_id}/comments", response_model=CommentOut, status_code=201)
async def add_comment_endpoint(
    ticket_id: uuid.UUID,
    body: CommentCreate,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    ticket = await get_ticket_for_user(db, ticket_id, user)
    cached = await get_idempotent(db, user, f"POST:/tickets/{ticket_id}/comments", idempotency_key)
    if cached:
        return cached
    comment = await add_comment(db, user, ticket, body.body, body.is_internal, idempotency_key)
    await db.commit()
    await db.refresh(comment)
    return await _comment_out(db, comment)


@router.post("/bulk", response_model=dict)
async def bulk_action(
    body: BulkTicketAction,
    user=Depends(require_permissions("ticket.update")),
    db: AsyncSession = Depends(get_db),
):
    updated = 0
    errors = []
    for tid in body.ticket_ids:
        try:
            ticket = await get_ticket_for_user(db, tid, user)
            if body.action == "assign" and body.payload.get("assignee_id"):
                ticket.assignee_id = uuid.UUID(body.payload["assignee_id"])
                ticket.version += 1
                updated += 1
            elif body.action == "status" and body.payload.get("status"):
                await transition_ticket(db, user, ticket, body.payload["status"])
                updated += 1
            elif body.action == "priority" and body.payload.get("priority"):
                ticket.priority = body.payload["priority"]
                ticket.version += 1
                updated += 1
        except Exception as exc:
            errors.append({"ticket_id": str(tid), "error": str(exc)})
    await db.commit()
    return {"updated": updated, "errors": errors}
