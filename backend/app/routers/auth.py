from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import User, RefreshToken, Tenant
from ..schemas import RegisterIn, LoginIn, RefreshIn, TokenOut, MeOut
from ..security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_record,
    refresh_hash,
    revoke_family,
)
from ..deps import current_user, get_tenant
from ..services.audit import audit_log
from ..services.tenancy import (
    create_tenant_with_owner,
    ensure_default_sla_policies,
    get_user_permissions,
    seed_permissions,
)
from ..utils import err

router = APIRouter()

_login_attempts: dict[str, list[datetime]] = defaultdict(list)


def _check_rate_limit(key: str, limit: int = 20):
    now = datetime.now(timezone.utc)
    window = [t for t in _login_attempts[key] if (now - t).total_seconds() < 60]
    _login_attempts[key] = window
    if len(window) >= limit:
        err(429, "RATE_LIMITED", "Too many attempts")
    window.append(now)


async def issue_tokens(db, user, family_id=None):
    raw_refresh, _rec = await create_refresh_record(db, user.id, family_id=family_id)
    return TokenOut(
        access_token=create_access_token(user.id, user.role, user.tenant_id),
        refresh_token=raw_refresh,
    )


@router.post("/register", response_model=TokenOut, status_code=201)
async def register(body: RegisterIn, db: AsyncSession = Depends(get_db)):
    _check_rate_limit(f"register:{body.email.lower()}")
    existing = (
        await db.execute(select(User).where(User.email == body.email.lower()))
    ).scalar_one_or_none()
    if existing:
        err(409, "CONFLICT", "Email already registered")
    await seed_permissions(db)
    tenant, user, _contact = await create_tenant_with_owner(
        db,
        tenant_name=body.tenant_name,
        email=body.email,
        full_name=body.full_name,
        password_hash=hash_password(body.password),
    )
    await ensure_default_sla_policies(db, tenant.id)
    tokens = await issue_tokens(db, user)
    await audit_log(db, user, "auth.register", "user", user.id, new_values={"tenant_id": str(tenant.id)})
    await db.commit()
    return tokens


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, request: Request, db: AsyncSession = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(f"login:{client_ip}:{body.email.lower()}")
    users = (
        await db.execute(select(User).where(User.email == body.email.lower()))
    ).scalars().all()
    if not users:
        err(401, "AUTH_INVALID", "Invalid email or password")
    user = users[0] if len(users) == 1 else None
    if len(users) > 1:
        err(401, "AUTH_INVALID", "Multiple accounts found; contact support")
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        err(401, "AUTH_INVALID", "Invalid email or password")
    tokens = await issue_tokens(db, user)
    await audit_log(db, user, "auth.login", "user", user.id)
    await db.commit()
    return tokens


@router.post("/refresh", response_model=TokenOut)
async def refresh(body: RefreshIn, db: AsyncSession = Depends(get_db)):
    token = (
        await db.execute(select(RefreshToken).where(RefreshToken.token_hash == refresh_hash(body.refresh_token)))
    ).scalar_one_or_none()
    if not token:
        err(401, "AUTH_REQUIRED", "Invalid refresh token")
    now = datetime.now(timezone.utc)
    if token.revoked_at is not None:
        await revoke_family(db, token.family_id)
        await db.commit()
        err(401, "REFRESH_TOKEN_REUSE", "Refresh-token reuse detected; token family revoked")
    if token.expires_at <= now:
        err(401, "AUTH_REQUIRED", "Refresh token expired")
    user = await db.get(User, token.user_id)
    if not user or not user.is_active:
        err(401, "AUTH_INVALID", "User is inactive")
    token.revoked_at = now
    raw, replacement = await create_refresh_record(db, user.id, family_id=token.family_id)
    token.replaced_by_id = replacement.id
    out = TokenOut(access_token=create_access_token(user.id, user.role, user.tenant_id), refresh_token=raw)
    await db.commit()
    return out


@router.post("/logout", status_code=204)
async def logout(body: RefreshIn, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    token = (
        await db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == refresh_hash(body.refresh_token),
                RefreshToken.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if token:
        await revoke_family(db, token.family_id)
        await audit_log(db, user, "auth.logout", "user", user.id)
        await db.commit()
    return Response(status_code=204)


@router.get("/me", response_model=MeOut)
async def me(user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    tenant = await get_tenant(db, user)
    perms = sorted(await get_user_permissions(db, user))
    return MeOut(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        user_type=user.user_type,
        is_active=user.is_active,
        permissions=perms,
        tenant_name=tenant.name,
    )
