from datetime import datetime, timedelta, timezone
import secrets
import uuid
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.errors import AppError, ConflictError, RateLimitError
from app.core.security import create_token, get_current_user, hash_password, hash_token, verify_password
from app.db.database import get_db
from .models import RefreshToken, User
from .schemas import LoginIn, RefreshIn, RegisterIn, TokenOut, UserOut
router = APIRouter(prefix="/auth", tags=["auth"])
_login_attempts: dict[str, list[float]] = {}
def enforce_login_limit(request: Request):
    import time
    ip = request.client.host if request.client else "unknown"; now = time.time(); attempts = [x for x in _login_attempts.get(ip, []) if x > now - settings.login_rate_window_seconds]
    if len(attempts) >= settings.login_rate_limit: raise RateLimitError()
    attempts.append(now); _login_attempts[ip] = attempts
def pair(user, family_id=None):
    family_id = family_id or uuid.uuid4()
    refresh = secrets.token_urlsafe(48); access = create_token(user.id, user.role, "access", timedelta(minutes=settings.access_token_minutes)); return access, refresh, family_id
@router.post("/register", response_model=TokenOut, status_code=201)
async def register(data: RegisterIn, db: AsyncSession = Depends(get_db)):
    if (await db.execute(select(User).where(User.email == data.email.lower()))).scalar_one_or_none(): raise ConflictError("Email already registered")
    user = User(email=data.email.lower(), full_name=data.full_name, password_hash=hash_password(data.password)); db.add(user); await db.flush(); access, refresh, family = pair(user); db.add(RefreshToken(user_id=user.id, token_hash=hash_token(refresh), family_id=family, expires_at=datetime.now(timezone.utc)+timedelta(days=settings.refresh_token_days))); await db.commit(); return TokenOut(access_token=access, refresh_token=refresh)
@router.post("/login", response_model=TokenOut)
async def login(request: Request, data: LoginIn, db: AsyncSession = Depends(get_db)):
    enforce_login_limit(request)
    user = (await db.execute(select(User).where(User.email == data.email.lower()))).scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash): raise AppError("AUTH_INVALID", "Invalid email or password", 401)
    access, refresh, family = pair(user); db.add(RefreshToken(user_id=user.id, token_hash=hash_token(refresh), family_id=family, expires_at=datetime.now(timezone.utc)+timedelta(days=settings.refresh_token_days))); await db.commit(); return TokenOut(access_token=access, refresh_token=refresh)
@router.post("/refresh", response_model=TokenOut)
async def refresh(data: RefreshIn, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(RefreshToken).where(RefreshToken.token_hash == hash_token(data.refresh_token)))).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if not row or row.expires_at <= now: raise AppError("AUTH_REQUIRED", "Invalid refresh token", 401)
    if row.revoked_at is not None or row.used_at is not None:
        await db.execute(RefreshToken.__table__.update().where(RefreshToken.family_id == row.family_id).values(revoked_at=now))
        await db.commit(); raise AppError("REFRESH_TOKEN_REUSE", "Refresh token reuse detected", 401)
    row.used_at = now; row.revoked_at = now; user = await db.get(User, row.user_id)
    if not user or not user.is_active: raise AppError("AUTH_REQUIRED", "Authentication required", 401)
    access, token, family = pair(user, row.family_id); db.add(RefreshToken(user_id=user.id, token_hash=hash_token(token), family_id=family, expires_at=now+timedelta(days=settings.refresh_token_days))); await db.commit(); return TokenOut(access_token=access, refresh_token=token)

@router.post("/logout", status_code=204)
async def logout(data: RefreshIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    await db.execute(RefreshToken.__table__.update().where(RefreshToken.user_id == user.id, RefreshToken.token_hash == hash_token(data.refresh_token)).values(revoked_at=datetime.now(timezone.utc)))
    await db.commit()
@router.get("/me", response_model=UserOut)
async def me(user=Depends(get_current_user)): return user
