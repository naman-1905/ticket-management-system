import uuid
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import require_roles
from app.core.errors import NotFoundError
from app.db.database import get_db
from .models import User
router=APIRouter(prefix="/users",tags=["users"])
@router.get("")
async def users(role:str|None=None,db:AsyncSession=Depends(get_db),user=Depends(require_roles("ADMIN","AGENT"))):
    q=select(User)
    if role:q=q.where(User.role==role)
    return (await db.execute(q.order_by(User.email))).scalars().all()
@router.patch("/{user_id}/role")
async def role(user_id:uuid.UUID,data:dict,db:AsyncSession=Depends(get_db),user=Depends(require_roles("ADMIN",))):
    target=await db.get(User,user_id)
    if not target:raise NotFoundError("User not found")
    target.role=data["role"];await db.commit();await db.refresh(target);return target
