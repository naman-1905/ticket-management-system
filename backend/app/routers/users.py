import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import User, Role, UserRole
from ..schemas import UserOut, RoleIn
from ..deps import current_user, require_permissions
from ..services.audit import audit_log
from ..services.tenancy import assign_user_role, get_user_permissions
from ..utils import err

router = APIRouter()


async def user_out(db: AsyncSession, user: User) -> UserOut:
    perms = sorted(await get_user_permissions(db, user))
    return UserOut(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        user_type=user.user_type,
        is_active=user.is_active,
        permissions=perms,
    )


@router.get("/agents", response_model=list[UserOut])
async def list_agents(user=Depends(require_permissions("ticket.assign")), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(User).where(
                User.tenant_id == user.tenant_id,
                User.user_type == "staff",
                User.is_active == True,  # noqa: E712
            ).order_by(User.full_name)
        )
    ).scalars().all()
    return [await user_out(db, u) for u in rows]


@router.get("", response_model=list[UserOut])
async def list_users(
    role: str | None = None,
    user=Depends(require_permissions("user.manage")),
    db: AsyncSession = Depends(get_db),
):
    q = select(User).where(User.tenant_id == user.tenant_id).order_by(User.email)
    if role:
        q = q.where(User.role == role)
    rows = (await db.execute(q)).scalars().all()
    return [await user_out(db, u) for u in rows]


@router.patch("/{user_id}/role", response_model=UserOut)
async def change_role(
    user_id: uuid.UUID,
    body: RoleIn,
    admin=Depends(require_permissions("user.manage")),
    db: AsyncSession = Depends(get_db),
):
    target = (
        await db.execute(select(User).where(User.id == user_id, User.tenant_id == admin.tenant_id))
    ).scalar_one_or_none()
    if not target:
        err(404, "NOT_FOUND", "User not found")
    if target.role == "OWNER" and body.role != "OWNER" and target.is_active:
        owners = (
            await db.execute(
                select(User).where(User.tenant_id == admin.tenant_id, User.role == "OWNER", User.is_active == True)  # noqa: E712
            )
        ).scalars().all()
        if len(owners) <= 1:
            err(409, "CONFLICT", "Cannot demote the last owner")
    old = {"role": target.role}
    target.role = body.role
    role_row = (
        await db.execute(select(Role).where(Role.tenant_id == admin.tenant_id, Role.name == body.role))
    ).scalar_one_or_none()
    if role_row:
        existing = (
            await db.execute(select(UserRole).where(UserRole.user_id == target.id))
        ).scalars().all()
        for ur in existing:
            await db.delete(ur)
        await assign_user_role(db, target, body.role)
    await audit_log(db, admin, "user.role_changed", "user", target.id, old, {"role": body.role})
    await db.commit()
    return await user_out(db, target)
