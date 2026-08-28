from datetime import datetime, timedelta, timezone
import hashlib, uuid, jwt
from argon2 import PasswordHasher
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.errors import AppError, ForbiddenError
from app.db.database import get_db
hasher = PasswordHasher(); oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
def hash_password(value: str) -> str: return hasher.hash(value)
def verify_password(value: str, hashed: str) -> bool:
    try: return hasher.verify(hashed, value)
    except Exception: return False
def hash_token(value: str) -> str: return hashlib.sha256(value.encode()).hexdigest()
def create_token(user_id: uuid.UUID, role: str, kind: str, expires: timedelta, family_id: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    claims = {"sub": str(user_id), "role": role, "type": kind, "jti": str(uuid.uuid4()), "iat": now, "exp": now + expires}
    if family_id: claims["family_id"] = family_id
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)
def decode_access(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "access": raise ValueError()
        return payload
    except Exception as exc: raise AppError("AUTH_REQUIRED", "Invalid or expired token", 401) from exc
async def get_current_user(db: AsyncSession = Depends(get_db), token: str = Depends(oauth2)):
    from app.modules.identity.models import User
    payload = decode_access(token)
    try: user = await db.get(User, uuid.UUID(payload["sub"]))
    except (KeyError, ValueError) as exc: raise AppError("AUTH_REQUIRED", "Authentication required", 401) from exc
    if not user or not user.is_active: raise AppError("AUTH_REQUIRED", "Authentication required", 401)
    return user
def require_roles(*roles):
    async def dependency(user=Depends(get_current_user)):
        if user.role not in roles: raise ForbiddenError("Insufficient permissions")
        return user
    return dependency
