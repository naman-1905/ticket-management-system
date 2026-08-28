from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import require_roles
from app.db.database import get_db
from .models import AuditLog
router=APIRouter(prefix="/audit",tags=["audit"])
@router.get("/logs")
async def logs(page:int=1,size:int=20,db:AsyncSession=Depends(get_db),user=Depends(require_roles("ADMIN",))):
    q=select(AuditLog).order_by(AuditLog.created_at.desc()); rows=(await db.execute(q.offset((page-1)*size).limit(min(size,100)))).scalars().all(); return {"items":rows,"page":page,"size":size}
