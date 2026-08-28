import uuid
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import ForbiddenError, NotFoundError
from app.modules.audit.models import AuditLog
from app.modules.sla.models import SLAPolicy, TicketSLA
from .events import event_bus
from app.core.idempotency import replay_or_none, store
from app.core.security import get_current_user, require_roles
from app.db.database import get_db
from .models import Comment, Ticket
from .schemas import Assignment, CommentCreate, CommentOut, TicketCreate, TicketOut, TicketStatus
from .state_machine import validate_transition
router = APIRouter(prefix="/tickets", tags=["tickets"])
def visible(ticket, user):
        if user.role == "CUSTOMER" and ticket.customer_id != user.id: raise ForbiddenError("Ticket does not belong to you")
async def audit(db, user, action, entity_id, old=None, new=None):
    db.add(AuditLog(actor_id=user.id, action=action, entity_type="ticket", entity_id=entity_id, old_values=old, new_values=new))
@router.post("", response_model=TicketOut, status_code=201)
async def create_ticket(data: TicketCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user), idempotency_key: str | None = Header(None)):
    body=data.model_dump(); cached=await replay_or_none(idempotency_key, body)
    if cached: return cached
    ticket = Ticket(ticket_number=f"TCK-{uuid.uuid4().hex[:12].upper()}", customer_id=user.id, created_by=user.id, **body); db.add(ticket); await db.flush()
    policy = (await db.execute(select(SLAPolicy).where(SLAPolicy.priority == ticket.priority, SLAPolicy.is_active.is_(True)).order_by(SLAPolicy.created_at))).scalars().first()
    if policy:
        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        db.add(TicketSLA(ticket_id=ticket.id, policy_id=policy.id, first_response_due_at=now + __import__("datetime").timedelta(minutes=policy.first_response_minutes), resolution_due_at=now + __import__("datetime").timedelta(hours=policy.resolution_hours)))
    await audit(db, user, "ticket.created", ticket.id, new=body); await db.commit(); await db.refresh(ticket)
    await event_bus.publish("ticket.created", {"ticket_id": str(ticket.id), "customer_id": str(user.id), "priority": ticket.priority})
    result=TicketOut.model_validate(ticket).model_dump(mode="json"); await store(idempotency_key, body, result); return ticket
@router.get("", response_model=dict)
async def list_tickets(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), status: str | None = None, priority: str | None = None, category: str | None = None, customer_id: uuid.UUID | None = None, assignee_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    q = select(Ticket); count = select(func.count(Ticket.id))
    if user.role == "CUSTOMER": q=q.where(Ticket.customer_id==user.id); count=count.where(Ticket.customer_id==user.id)
    if user.role != "CUSTOMER" and customer_id is not None: q=q.where(Ticket.customer_id==customer_id); count=count.where(Ticket.customer_id==customer_id)
    for col, val in ((Ticket.status,status),(Ticket.priority,priority),(Ticket.category,category),(Ticket.assignee_id,assignee_id)):
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
    visible(ticket,user); validate_transition(ticket.status,data.status,user.role); old=ticket.status; ticket.status=data.status; await audit(db,user,"ticket.status_changed",ticket.id,old={"status":old},new={"status":data.status}); await db.commit(); await db.refresh(ticket); await event_bus.publish("ticket.status_changed", {"ticket_id":str(ticket.id),"old_status":old,"new_status":data.status,"actor_id":str(user.id)}); return ticket
@router.post("/{ticket_id}/assign", response_model=TicketOut)
async def assign(ticket_id: uuid.UUID, data: Assignment, db: AsyncSession = Depends(get_db), user=Depends(require_roles("AGENT","ADMIN"))):
    ticket=await db.get(Ticket,ticket_id)
    if not ticket: raise NotFoundError("Ticket not found")
    assignee = await db.get(__import__("app.modules.identity.models", fromlist=["User"]).User, data.assignee_id)
    if not assignee or assignee.role not in {"AGENT", "ADMIN"} or not assignee.is_active: raise NotFoundError("Active agent not found")
    ticket.assignee_id=data.assignee_id; await audit(db,user,"ticket.assigned",ticket.id,new={"assignee_id":str(data.assignee_id)}); await db.commit(); await db.refresh(ticket); await event_bus.publish("ticket.assigned", {"ticket_id":str(ticket.id),"assignee_id":str(data.assignee_id),"actor_id":str(user.id)}); return ticket
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
    await audit(db,user,"comment.added",ticket.id,new={"comment_id":str(comment.id),"is_internal":comment.is_internal}); await db.commit(); await store(idempotency_key, body, CommentOut.model_validate(comment).model_dump(mode="json")); await event_bus.publish("comment.added", {"ticket_id":str(ticket.id),"author_id":str(user.id),"is_internal":comment.is_internal}); return comment
