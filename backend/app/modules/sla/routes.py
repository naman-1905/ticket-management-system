import uuid
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import NotFoundError
from app.core.security import get_current_user, require_roles
from app.db.database import get_db
from .models import SLAPolicy, TicketSLA
router=APIRouter(tags=["sla"])
class SLAPolicyIn(BaseModel):
    name: str = Field(min_length=1, max_length=100); priority: str = Field(pattern="^P[1-4]$"); first_response_minutes: int = Field(gt=0); resolution_hours: int = Field(gt=0); is_active: bool = True
@router.get("/sla/policies")
async def policies(db:AsyncSession=Depends(get_db), user=Depends(require_roles("AGENT","ADMIN"))): return (await db.execute(select(SLAPolicy).where(SLAPolicy.is_active==True))).scalars().all()
@router.post("/sla/policies",status_code=201)
async def create_policy(data:SLAPolicyIn,db:AsyncSession=Depends(get_db),user=Depends(require_roles("ADMIN",))):
    item=SLAPolicy(**data.model_dump());db.add(item);await db.commit();await db.refresh(item);return item
@router.patch("/sla/policies/{policy_id}")
async def update_policy(policy_id:uuid.UUID,data:SLAPolicyIn,db:AsyncSession=Depends(get_db),user=Depends(require_roles("ADMIN",))):
    item=await db.get(SLAPolicy,policy_id)
    if not item: raise NotFoundError("SLA policy not found")
    for key,val in data.model_dump().items(): setattr(item,key,val)
    await db.commit();await db.refresh(item);return item
@router.get("/tickets/{ticket_id}/sla")
async def ticket_sla(ticket_id:uuid.UUID,db:AsyncSession=Depends(get_db),user=Depends(get_current_user)):
    from app.modules.ticketing.models import Ticket
    ticket=await db.get(Ticket,ticket_id)
    if not ticket: raise NotFoundError("Ticket not found")
    if user.role=="CUSTOMER" and ticket.customer_id != user.id: raise NotFoundError("Ticket not found")
    item=(await db.execute(select(TicketSLA).where(TicketSLA.ticket_id==ticket_id))).scalar_one_or_none()
    return item or {"ticket_id":ticket_id,"status":"PENDING"}
