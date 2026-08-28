import uuid
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import require_roles
from app.core.errors import NotFoundError
from app.db.database import get_db
from .models import User
from .schemas import RoleUpdate
router=APIRouter(prefix="/users",tags=["users"])
@router.get("")
async def users(role:str|None=None,db:AsyncSession=Depends(get_db),user=Depends(require_roles("ADMIN","AGENT"))):
    q=select(User)
    if role:q=q.where(User.role==role)
    return (await db.execute(q.order_by(User.email))).scalars().all()
@router.patch("/{user_id}/role")
async def role(user_id:uuid.UUID,data:RoleUpdate,db:AsyncSession=Depends(get_db),user=Depends(require_roles("ADMIN",))):
    target=await db.get(User,user_id)
    if not target:raise NotFoundError("User not found")
    if target.id == user.id and data.role != "ADMIN":
        admins = await db.scalar(select(func.count(User.id)).where(User.role == "ADMIN", User.is_active.is_(True)))
        if admins <= 1: from app.core.errors import ConflictError; raise ConflictError("Cannot demote the last active administrator")
    target.role=data.role;await db.commit();await db.refresh(target);return target
