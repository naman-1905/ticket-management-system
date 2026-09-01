from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import jwt

from .core.errors import raise_api_error
from .db import get_db
from .models import User, Tenant
from .security import decode_access_token
from .services.tenancy import get_user_permissions

bearer = HTTPBearer(auto_error=False)


async def current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise_api_error(401, "AUTH_REQUIRED", "Authentication required")
    try:
        payload = decode_access_token(credentials.credentials)
        if payload.get("type") != "access":
            raise ValueError()
        user_id = payload["sub"]
    except Exception:
        raise_api_error(401, "AUTH_INVALID", "Invalid or expired token")
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise_api_error(401, "AUTH_INVALID", "Invalid or inactive user")
    request.state.user = user
    return user


def require_permissions(*permissions: str):
    async def checker(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
        user_perms = await get_user_permissions(db, user)
        if user.is_platform_admin:
            return user
        if not all(p in user_perms for p in permissions):
            raise_api_error(403, "FORBIDDEN", "Insufficient permissions")
        return user

    return checker


def require_roles(*roles: str):
    async def checker(user: User = Depends(current_user)):
        if user.role not in roles and not user.is_platform_admin:
            raise_api_error(403, "FORBIDDEN", "Insufficient role")
        return user

    return checker


async def get_tenant(db: AsyncSession, user: User) -> Tenant:
    tenant = await db.get(Tenant, user.tenant_id)
    if not tenant or not tenant.is_active:
        raise_api_error(403, "FORBIDDEN", "Tenant inactive")
    return tenant
