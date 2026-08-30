import secrets, uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Header
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from ..models import Ticket, Comment, User, SLAPolicy, TicketSLA
from ..schemas import TicketCreate, TicketOut, TicketStatus, Assignment, CommentCreate, CommentOut, Page
from ..deps import current_user, require_roles
from ..utils import err, audit, get_idempotent, save_idempotent

router=APIRouter()
TRANSITIONS={
 "CUSTOMER":{"OPEN":{"CLOSED"},"RESOLVED":{"CLOSED"}},
 "AGENT":{"OPEN":{"IN_PROGRESS","ON_HOLD","RESOLVED"},"IN_PROGRESS":{"ON_HOLD","RESOLVED","CLOSED"},"ON_HOLD":{"IN_PROGRESS","RESOLVED"},"RESOLVED":{"CLOSED","OPEN"},"CLOSED":set()},
 "ADMIN":{"OPEN":{"IN_PROGRESS","ON_HOLD","RESOLVED","CLOSED"},"IN_PROGRESS":{"OPEN","ON_HOLD","RESOLVED","CLOSED"},"ON_HOLD":{"OPEN","IN_PROGRESS","RESOLVED","CLOSED"},"RESOLVED":{"OPEN","CLOSED"},"CLOSED":{"OPEN"}}
}

def ticket_json(t):
    return TicketOut.model_validate(t).model_dump(mode="json")

@router.post("",response_model=TicketOut,status_code=201)
async def create_ticket(body:TicketCreate,user=Depends(current_user),db:AsyncSession=Depends(get_db),idempotency_key:str|None=Header(default=None,alias="Idempotency-Key")):
    old=await get_idempotent(db,user.id,"POST:/tickets",idempotency_key)
    if old: return old.response_body
    t=Ticket(
    ticket_number="TCK-" + secrets.token_hex(6).upper(),
    title=body.title,
    description=body.description,
    priority=body.priority,
    category=body.category,
    customer_id=user.id,
    created_by=user.id,
)
    db.add(t); await db.flush()
    policy=(await db.execute(select(SLAPolicy).where(SLAPolicy.priority==body.priority,SLAPolicy.is_active==True).order_by(SLAPolicy.created_at))).scalars().first()
    if policy:
        created=t.created_at
        db.add(TicketSLA(ticket_id=t.id,policy_id=policy.id,first_response_due_at=created+timedelta(minutes=policy.first_response_minutes),resolution_due_at=created+timedelta(hours=policy.resolution_hours)))
    await audit(db,user.id,"ticket.created","ticket",t.id,new_values=ticket_json(t))
    result=ticket_json(t)
    await save_idempotent(db,user.id,"POST:/tickets",idempotency_key,201,result)
    await db.commit()
    return result

@router.get("",response_model=Page[TicketOut])
async def list_tickets(page:int=1,size:int=20,status:str|None=None,priority:str|None=None,category:str|None=None,customer_id:uuid.UUID|None=None,assignee_id:uuid.UUID|None=None,user=Depends(current_user),db:AsyncSession=Depends(get_db)):
    page=max(page,1); size=min(max(size,1),100)
    q=select(Ticket)
    if user.role=="CUSTOMER": q=q.where(Ticket.customer_id==user.id)
    elif customer_id: q=q.where(Ticket.customer_id==customer_id)
    if status:q=q.where(Ticket.status==status)
    if priority:q=q.where(Ticket.priority==priority)
    if category:q=q.where(Ticket.category==category)
    if assignee_id:q=q.where(Ticket.assignee_id==assignee_id)
    total=await db.scalar(select(func.count()).select_from(q.subquery()))
    rows=(await db.execute(q.order_by(Ticket.created_at.desc()).offset((page-1)*size).limit(size))).scalars().all()
    return {"items":rows,"total":total or 0,"page":page,"size":size}

async def get_ticket(ticket_id,user,db):
    t=await db.get(Ticket,ticket_id)
    if not t: err(404,"NOT_FOUND","Ticket not found")
    if user.role=="CUSTOMER" and t.customer_id!=user.id: err(403,"FORBIDDEN","Ticket is not owned by user")
    return t

@router.get("/{ticket_id}",response_model=TicketOut)
async def get_one(ticket_id:uuid.UUID,user=Depends(current_user),db:AsyncSession=Depends(get_db)):
    return await get_ticket(ticket_id,user,db)

@router.patch("/{ticket_id}/status",response_model=TicketOut)
async def change_status(ticket_id:uuid.UUID,body:TicketStatus,user=Depends(current_user),db:AsyncSession=Depends(get_db)):
    t=await get_ticket(ticket_id,user,db)
    if body.status not in TRANSITIONS.get(user.role,{}).get(t.status,set()): err(403,"FORBIDDEN",f"Invalid status transition from {t.status} to {body.status}")
    old={"status":t.status}; t.status=body.status
    if body.status=="RESOLVED":
        sla=(await db.execute(select(TicketSLA).where(TicketSLA.ticket_id==t.id))).scalar_one_or_none()
        if sla: sla.resolved_at=datetime.now(timezone.utc)
    await audit(db,user.id,"ticket.status_changed","ticket",t.id,old,{"status":t.status})
    await db.commit(); return t

@router.post("/{ticket_id}/assign",response_model=TicketOut)
async def assign(ticket_id:uuid.UUID,body:Assignment,user=Depends(require_roles("AGENT","ADMIN")),db:AsyncSession=Depends(get_db)):
    t=await get_ticket(ticket_id,user,db)
    assignee=await db.get(User,body.assignee_id)
    if not assignee or not assignee.is_active or assignee.role not in ("AGENT","ADMIN"): err(404,"NOT_FOUND","Active agent not found")
    old={"assignee_id":str(t.assignee_id) if t.assignee_id else None}; t.assignee_id=assignee.id
    await audit(db,user.id,"ticket.assigned","ticket",t.id,old,{"assignee_id":str(assignee.id)})
    await db.commit(); return t

@router.get("/{ticket_id}/comments",response_model=list[CommentOut])
async def comments(ticket_id:uuid.UUID,user=Depends(current_user),db:AsyncSession=Depends(get_db)):
    t=await get_ticket(ticket_id,user,db)
    q=select(Comment).where(Comment.ticket_id==t.id).order_by(Comment.created_at)
    if user.role=="CUSTOMER": q=q.where(Comment.is_internal==False)
    return (await db.execute(q)).scalars().all()

@router.post("/{ticket_id}/comments",response_model=CommentOut,status_code=201)
async def add_comment(ticket_id:uuid.UUID,body:CommentCreate,user=Depends(current_user),db:AsyncSession=Depends(get_db),idempotency_key:str|None=Header(default=None,alias="Idempotency-Key")):
    t=await get_ticket(ticket_id,user,db)
    if user.role=="CUSTOMER" and body.is_internal: err(403,"FORBIDDEN","Customers cannot create internal comments")
    old=await get_idempotent(db,user.id,f"POST:/tickets/{ticket_id}/comments",idempotency_key)
    if old: return old.response_body
    c=Comment(ticket_id=t.id,author_id=user.id,body=body.body,is_internal=body.is_internal); db.add(c); await db.flush()
    result=CommentOut.model_validate(c).model_dump(mode="json")
    await audit(db,user.id,"comment.added","comment",c.id,new_values=result)
    await save_idempotent(db,user.id,f"POST:/tickets/{ticket_id}/comments",idempotency_key,201,result)
    await db.commit(); return result
