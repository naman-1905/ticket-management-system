import uuid
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from ..models import SLAPolicy, TicketSLA
from ..schemas import SLAPolicyIn, SLAPolicyOut, TicketSLAOut
from ..deps import current_user, require_roles
from ..routers.tickets import get_ticket
from ..utils import err, audit

router=APIRouter()

@router.get("/sla/policies",response_model=list[SLAPolicyOut])
async def policies(user=Depends(require_roles("AGENT","ADMIN")),db:AsyncSession=Depends(get_db)):
    return (await db.execute(select(SLAPolicy).where(SLAPolicy.is_active==True).order_by(SLAPolicy.priority))).scalars().all()

@router.post("/sla/policies",response_model=SLAPolicyOut,status_code=201)
async def create_policy(body:SLAPolicyIn,user=Depends(require_roles("ADMIN")),db:AsyncSession=Depends(get_db)):
    exists=(await db.execute(select(SLAPolicy).where(SLAPolicy.name==body.name))).scalar_one_or_none()
    if exists: err(409,"CONFLICT","SLA policy name already exists")
    p=SLAPolicy(**body.model_dump()); db.add(p); await db.flush()
    await audit(db,user.id,"sla.policy_created","sla_policy",p.id,new_values=body.model_dump())
    await db.commit(); return p

@router.patch("/sla/policies/{policy_id}",response_model=SLAPolicyOut)
async def update_policy(policy_id:uuid.UUID,body:SLAPolicyIn,user=Depends(require_roles("ADMIN")),db:AsyncSession=Depends(get_db)):
    p=await db.get(SLAPolicy,policy_id)
    if not p: err(404,"NOT_FOUND","SLA policy not found")
    p.name=body.name;p.priority=body.priority;p.first_response_minutes=body.first_response_minutes;p.resolution_hours=body.resolution_hours;p.is_active=body.is_active
    await audit(db,user.id,"sla.policy_updated","sla_policy",p.id,new_values=body.model_dump())
    await db.commit(); return p

@router.get("/tickets/{ticket_id}/sla",response_model=TicketSLAOut|dict)
async def ticket_sla(ticket_id:uuid.UUID,user=Depends(current_user),db:AsyncSession=Depends(get_db)):
    t=await get_ticket(ticket_id,user,db)
    row=(await db.execute(select(TicketSLA).where(TicketSLA.ticket_id==t.id))).scalar_one_or_none()
    if not row: return {"ticket_id":t.id,"status":"PENDING"}
    return row
