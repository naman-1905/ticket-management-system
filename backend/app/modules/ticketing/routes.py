import uuid
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import ForbiddenError, NotFoundError
from app.core.idempotency import replay_or_none, store
from app.core.security import get_current_user, require_roles
from app.db.database import get_db
from .models import Comment, Ticket
from .schemas import Assignment, CommentCreate, CommentOut, TicketCreate, TicketOut, TicketStatus
from .state_machine import validate_transition
router = APIRouter(prefix="/tickets", tags=["tickets"])
def visible(ticket, user):
    if user.role == "CUSTOMER" and ticket.customer_id != user.id: raise ForbiddenError("Ticket does not belong to you")
@router.post("", response_model=TicketOut, status_code=201)
async def create_ticket(data: TicketCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user), idempotency_key: str | None = Header(None)):
    body=data.model_dump(); cached=await replay_or_none(idempotency_key, body)
    if cached: return cached
    ticket = Ticket(ticket_number=f"TCK-{uuid.uuid4().hex[:12].upper()}", customer_id=user.id, created_by=user.id, **body); db.add(ticket); await db.commit(); await db.refresh(ticket)
    result=TicketOut.model_validate(ticket).model_dump(mode="json"); await store(idempotency_key, body, result); return ticket
@router.get("", response_model=dict)
async def list_tickets(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), status: str | None = None, priority: str | None = None, assignee_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    q = select(Ticket); count = select(func.count(Ticket.id))
    if user.role == "CUSTOMER": q=q.where(Ticket.customer_id==user.id); count=count.where(Ticket.customer_id==user.id)
    for col, val in ((Ticket.status,status),(Ticket.priority,priority),(Ticket.assignee_id,assignee_id)):
        if val is not None: q=q.where(col==val); count=count.where(col==val)
    total=(await db.execute(count)).scalar_one(); rows=(await db.execute(q.order_by(Ticket.created_at.desc()).offset((page-1)*size).limit(size))).scalars().all(); return {"items": rows, "total": total, "page": page, "size": size}
@router.get("/{ticket_id}", response_model=TicketOut)
async def get_ticket(ticket_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    ticket=await db.get(Ticket,ticket_id)
    if not ticket: raise NotFoundError("Ticket not found")
    visible(ticket,user); return ticket
@router.patch("/{ticket_id}/status", response_model=TicketOut)
async def update_status(ticket_id: uuid.UUID, data: TicketStatus, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    ticket=await db.get(Ticket,ticket_id)
    if not ticket: raise NotFoundError("Ticket not found")
    visible(ticket,user); validate_transition(ticket.status,data.status,user.role); ticket.status=data.status; await db.commit(); await db.refresh(ticket); return ticket
@router.post("/{ticket_id}/assign", response_model=TicketOut)
async def assign(ticket_id: uuid.UUID, data: Assignment, db: AsyncSession = Depends(get_db), user=Depends(require_roles("AGENT","ADMIN"))):
    ticket=await db.get(Ticket,ticket_id)
    if not ticket: raise NotFoundError("Ticket not found")
    ticket.assignee_id=data.assignee_id; await db.commit(); await db.refresh(ticket); return ticket
@router.get("/{ticket_id}/comments", response_model=list[CommentOut])
async def comments(ticket_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    ticket=await db.get(Ticket,ticket_id)
    if not ticket: raise NotFoundError("Ticket not found")
    visible(ticket,user); q=select(Comment).where(Comment.ticket_id==ticket_id); rows=(await db.execute(q)).scalars().all(); return rows if user.role != "CUSTOMER" else [x for x in rows if not x.is_internal]
@router.post("/{ticket_id}/comments", response_model=CommentOut, status_code=201)
async def add_comment(ticket_id: uuid.UUID, data: CommentCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user), idempotency_key: str | None = Header(None)):
    ticket=await db.get(Ticket,ticket_id)
    if not ticket: raise NotFoundError("Ticket not found")
    visible(ticket,user)
    if data.is_internal and user.role == "CUSTOMER": raise ForbiddenError("Customers cannot create internal comments")
    body={"ticket_id": str(ticket_id), **data.model_dump()}; cached=await replay_or_none(idempotency_key, body)
    if cached: return cached
    comment=Comment(ticket_id=ticket_id,author_id=user.id,**data.model_dump()); db.add(comment); await db.commit(); await db.refresh(comment)
    await store(idempotency_key, body, CommentOut.model_validate(comment).model_dump(mode="json")); return comment
