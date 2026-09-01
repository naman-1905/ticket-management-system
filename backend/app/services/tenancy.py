import re
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.permissions import DEFAULT_ROLES, PERMISSIONS
from ..models import (
    Tenant,
    User,
    Permission,
    Role,
    RolePermission,
    UserRole,
    Contact,
    Organization,
    SLAPolicy,
    SLAPolicyVersion,
)


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:80] or "tenant"


async def seed_permissions(db: AsyncSession):
    existing = (await db.execute(select(Permission.code))).scalars().all()
    existing_set = set(existing)
    for code in PERMISSIONS:
        if code not in existing_set:
            db.add(Permission(code=code, description=code))
    await db.flush()


async def seed_tenant_roles(db: AsyncSession, tenant_id: uuid.UUID):
    perm_rows = (await db.execute(select(Permission))).scalars().all()
    perm_by_code = {p.code: p for p in perm_rows}
    for role_name, perm_codes in DEFAULT_ROLES.items():
        role = Role(tenant_id=tenant_id, name=role_name, is_system=True)
        db.add(role)
        await db.flush()
        for code in perm_codes:
            perm = perm_by_code.get(code)
            if perm:
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    await db.flush()


async def assign_user_role(db: AsyncSession, user: User, role_name: str):
    role = (
        await db.execute(
            select(Role).where(Role.tenant_id == user.tenant_id, Role.name == role_name)
        )
    ).scalar_one_or_none()
    if not role:
        return
    existing = (
        await db.execute(select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id))
    ).scalar_one_or_none()
    if not existing:
        db.add(UserRole(user_id=user.id, role_id=role.id))


async def get_user_permissions(db: AsyncSession, user: User) -> set[str]:
    rows = (
        await db.execute(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user.id)
        )
    ).scalars().all()
    if rows:
        return set(rows)
    # Fallback to legacy role field
    legacy = DEFAULT_ROLES.get(user.role, DEFAULT_ROLES.get("CUSTOMER", []))
    return set(legacy)


async def user_has_permission(db: AsyncSession, user: User, permission: str) -> bool:
    if user.is_platform_admin:
        return True
    perms = await get_user_permissions(db, user)
    return permission in perms


async def create_tenant_with_owner(
    db: AsyncSession,
    *,
    tenant_name: str,
    email: str,
    full_name: str,
    password_hash: str,
) -> tuple[Tenant, User, Contact]:
    tenant = Tenant(name=tenant_name, slug=slugify(tenant_name))
    db.add(tenant)
    await db.flush()
    await seed_tenant_roles(db, tenant.id)
    user = User(
        tenant_id=tenant.id,
        email=email.lower(),
        full_name=full_name,
        password_hash=password_hash,
        role="OWNER",
        user_type="staff",
    )
    db.add(user)
    await db.flush()
    await assign_user_role(db, user, "OWNER")
    org = Organization(tenant_id=tenant.id, name=tenant_name, org_type="internal")
    db.add(org)
    await db.flush()
    contact = Contact(
        tenant_id=tenant.id,
        organization_id=org.id,
        user_id=user.id,
        email=email.lower(),
        full_name=full_name,
    )
    db.add(contact)
    await db.flush()
    return tenant, user, contact


async def ensure_default_sla_policies(db: AsyncSession, tenant_id: uuid.UUID):
    defaults = [
        ("P1 Critical", "P1", 15, 4),
        ("P2 High", "P2", 30, 8),
        ("P3 Normal", "P3", 60, 24),
        ("P4 Low", "P4", 240, 72),
    ]
    for name, priority, fr, res in defaults:
        exists = (
            await db.execute(
                select(SLAPolicy).where(SLAPolicy.tenant_id == tenant_id, SLAPolicy.priority == priority)
            )
        ).scalar_one_or_none()
        if exists:
            continue
        policy = SLAPolicy(
            tenant_id=tenant_id,
            name=name,
            priority=priority,
            first_response_minutes=fr,
            resolution_hours=res,
            is_active=True,
        )
        db.add(policy)
        await db.flush()
        db.add(
            SLAPolicyVersion(
                policy_id=policy.id,
                version=1,
                first_response_minutes=fr,
                resolution_hours=res,
            )
        )
    await db.flush()
