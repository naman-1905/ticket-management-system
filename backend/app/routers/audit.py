import uuid
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from ..models import AuditLog
from ..schemas import AuditLogOut, Page
from ..deps import require_roles

router=APIRouter()

@router.get("/logs",response_model=Page[AuditLogOut])
async def logs(page:int=1,size:int=20,entity_type:str|None=None,entity_id:uuid.UUID|None=None,actor_id:uuid.UUID|None=None,user=Depends(require_roles("ADMIN")),db:AsyncSession=Depends(get_db)):
    page=max(page,1); size=min(max(size,1),100)
    q=select(AuditLog)
    if entity_type:q=q.where(AuditLog.entity_type==entity_type)
    if entity_id:q=q.where(AuditLog.entity_id==entity_id)
    if actor_id:q=q.where(AuditLog.actor_id==actor_id)
    total=await db.scalar(select(func.count()).select_from(q.subquery()))
    rows=(await db.execute(q.order_by(AuditLog.created_at.desc()).offset((page-1)*size).limit(size))).scalars().all()
    return {"items":rows,"total":total or 0,"page":page,"size":size}
