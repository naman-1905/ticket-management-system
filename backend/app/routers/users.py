import uuid
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from ..models import User
from ..schemas import UserDBOut, RoleIn
from ..deps import require_roles
from ..utils import err, audit

router=APIRouter()

@router.get("", response_model=list[UserDBOut])
async def list_users(role: str|None=None, user=Depends(require_roles("AGENT","ADMIN")), db: AsyncSession=Depends(get_db)):
    q=select(User).order_by(User.email)
    if role: q=q.where(User.role==role)
    return (await db.execute(q)).scalars().all()

@router.patch("/{user_id}/role", response_model=UserDBOut)
async def change_role(user_id: uuid.UUID, body: RoleIn, admin=Depends(require_roles("ADMIN")), db: AsyncSession=Depends(get_db)):
    user=await db.get(User,user_id)
    if not user: err(404,"NOT_FOUND","User not found")
    if user.role=="ADMIN" and body.role!="ADMIN" and user.is_active:
        admins=(await db.execute(select(User).where(User.role=="ADMIN",User.is_active==True))).scalars().all()
        if len(admins)<=1: err(409,"CONFLICT","Cannot demote the last active administrator")
    old={"role":user.role}
    user.role=body.role
    await audit(db,admin.id,"user.role_changed","user",user.id,old,{"role":body.role})
    await db.commit()
    return user
