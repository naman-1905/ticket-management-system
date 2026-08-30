from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
from .db import get_db
from .models import User
from .security import decode_access_token

bearer = HTTPBearer(auto_error=False)

async def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: AsyncSession = Depends(get_db)):
    if not credentials:
        raise HTTPException(status_code=401, detail={"code":"AUTH_REQUIRED","message":"Authentication required","details":{}})
    try:
        payload = decode_access_token(credentials.credentials)
        if payload.get("type") != "access":
            raise ValueError()
        user_id = payload["sub"]
    except Exception:
        raise HTTPException(status_code=401, detail={"code":"AUTH_INVALID","message":"Invalid or expired token","details":{}})
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail={"code":"AUTH_INVALID","message":"Invalid or inactive user","details":{}})
    return user

def require_roles(*roles):
    async def checker(user=Depends(current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail={"code":"FORBIDDEN","message":"Insufficient role","details":{}})
        return user
    return checker
