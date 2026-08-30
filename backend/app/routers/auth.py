import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import Response
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from ..models import User, RefreshToken
from ..schemas import RegisterIn, LoginIn, RefreshIn, TokenOut, UserOut
from ..security import hash_password, verify_password, create_access_token, create_refresh_record, refresh_hash, revoke_family
from ..deps import current_user
from ..utils import err

router = APIRouter()

async def issue_tokens(db, user, family_id=None):
    raw_refresh, rec = await create_refresh_record(db, user.id, family_id=family_id)
    return TokenOut(access_token=create_access_token(user.id, user.role), refresh_token=raw_refresh)

@router.post("/register", response_model=TokenOut, status_code=201)
async def register(body: RegisterIn, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(User).where(User.email == body.email.lower()))).scalar_one_or_none()
    if existing:
        err(409,"CONFLICT","Email already registered")
    count = await db.scalar(select(func.count()).select_from(User))
    role = "ADMIN" if count == 0 else "CUSTOMER"
    user = User(email=body.email.lower(), full_name=body.full_name, password_hash=hash_password(body.password), role=role)
    db.add(user)
    await db.flush()
    tokens = await issue_tokens(db,user)
    await db.commit()
    return tokens

@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == body.email.lower()))).scalar_one_or_none()
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        err(401,"AUTH_INVALID","Invalid email or password")
    tokens = await issue_tokens(db,user)
    await db.commit()
    return tokens

@router.post("/refresh", response_model=TokenOut)
async def refresh(body: RefreshIn, db: AsyncSession = Depends(get_db)):
    token = (await db.execute(select(RefreshToken).where(RefreshToken.token_hash == refresh_hash(body.refresh_token)))).scalar_one_or_none()
    if not token:
        err(401,"AUTH_REQUIRED","Invalid refresh token")
    now = datetime.now(timezone.utc)
    if token.revoked_at is not None:
        await revoke_family(db, token.family_id)
        await db.commit()
        err(401,"REFRESH_TOKEN_REUSE","Refresh-token reuse detected; token family revoked")
    if token.expires_at <= now:
        err(401,"AUTH_REQUIRED","Refresh token expired")
    user = await db.get(User, token.user_id)
    if not user or not user.is_active:
        err(401,"AUTH_INVALID","User is inactive")
    token.revoked_at = now
    raw, replacement = await create_refresh_record(db,user.id,family_id=token.family_id)
    token.replaced_by_id = replacement.id
    out = TokenOut(access_token=create_access_token(user.id,user.role), refresh_token=raw)
    await db.commit()
    return out

@router.post("/logout", status_code=204)
async def logout(body: RefreshIn, user=Depends(current_user), db: AsyncSession=Depends(get_db)):
    token = (await db.execute(select(RefreshToken).where(
        RefreshToken.token_hash==refresh_hash(body.refresh_token), RefreshToken.user_id==user.id
    ))).scalar_one_or_none()
    if token:
        token.revoked_at = datetime.now(timezone.utc)
        await db.commit()
    return Response(status_code=204)

@router.get("/me", response_model=UserOut)
async def me(user=Depends(current_user)):
    return user
