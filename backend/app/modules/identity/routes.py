from datetime import datetime, timedelta, timezone
import uuid
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.errors import AppError, ConflictError
from app.core.security import create_token, get_current_user, hash_password, hash_token, verify_password
from app.db.database import get_db
from .models import RefreshToken, User
from .schemas import LoginIn, RefreshIn, RegisterIn, TokenOut, UserOut
router = APIRouter(prefix="/auth", tags=["auth"])
def pair(user):
    refresh = create_token(user.id, user.role, "refresh", timedelta(days=settings.refresh_token_days)); access = create_token(user.id, user.role, "access", timedelta(minutes=settings.access_token_minutes)); return access, refresh
@router.post("/register", response_model=TokenOut, status_code=201)
async def register(data: RegisterIn, db: AsyncSession = Depends(get_db)):
    if (await db.execute(select(User).where(User.email == data.email.lower()))).scalar_one_or_none(): raise ConflictError("Email already registered")
    user = User(email=data.email.lower(), full_name=data.full_name, password_hash=hash_password(data.password)); db.add(user); await db.flush(); access, refresh = pair(user); db.add(RefreshToken(user_id=user.id, token_hash=hash_token(refresh), expires_at=datetime.now(timezone.utc)+timedelta(days=settings.refresh_token_days))); await db.commit(); return TokenOut(access_token=access, refresh_token=refresh)
@router.post("/login", response_model=TokenOut)
async def login(data: LoginIn, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == data.email.lower()))).scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash): raise AppError("AUTH_INVALID", "Invalid email or password", 401)
    access, refresh = pair(user); db.add(RefreshToken(user_id=user.id, token_hash=hash_token(refresh), expires_at=datetime.now(timezone.utc)+timedelta(days=settings.refresh_token_days))); await db.commit(); return TokenOut(access_token=access, refresh_token=refresh)
@router.post("/refresh", response_model=TokenOut)
async def refresh(data: RefreshIn, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(RefreshToken).where(RefreshToken.token_hash == hash_token(data.refresh_token), RefreshToken.revoked_at.is_(None)))).scalar_one_or_none()
    if not row or row.expires_at <= datetime.now(timezone.utc): raise AppError("AUTH_REQUIRED", "Invalid refresh token", 401)
    row.revoked_at = datetime.now(timezone.utc); user = await db.get(User, row.user_id); access, token = pair(user); db.add(RefreshToken(user_id=user.id, token_hash=hash_token(token), expires_at=datetime.now(timezone.utc)+timedelta(days=settings.refresh_token_days))); await db.commit(); return TokenOut(access_token=access, refresh_token=token)
@router.get("/me", response_model=UserOut)
async def me(user=Depends(get_current_user)): return user
