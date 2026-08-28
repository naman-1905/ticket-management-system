from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import require_roles
from app.db.database import get_db
from .models import AuditLog
router=APIRouter(prefix="/audit",tags=["audit"])
@router.get("/logs")
async def logs(page:int=Query(1,ge=1),size:int=Query(20,ge=1,le=100),entity_type:str|None=None,entity_id:UUID|None=None,actor_id:UUID|None=None,db:AsyncSession=Depends(get_db),user=Depends(require_roles("ADMIN",))):
    q=select(AuditLog); count=select(func.count(AuditLog.id))
    for col,val in ((AuditLog.entity_type,entity_type),(AuditLog.entity_id,entity_id),(AuditLog.actor_id,actor_id)):
        if val is not None: q=q.where(col==val); count=count.where(col==val)
    rows=(await db.execute(q.order_by(AuditLog.created_at.desc()).offset((page-1)*size).limit(size))).scalars().all(); total=await db.scalar(count)
    return {"items":rows,"total":total,"page":page,"size":size}
