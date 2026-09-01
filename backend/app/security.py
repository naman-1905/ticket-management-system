import hashlib, secrets, uuid
from datetime import datetime, timedelta, timezone
import jwt
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .config import settings
from .models import RefreshToken

password_hash = PasswordHash.recommended()
ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)

def create_access_token(user_id: uuid.UUID, role: str, tenant_id: uuid.UUID | None = None) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "role": role, "type": "access", "exp": exp}
    if tenant_id:
        payload["tenant_id"] = str(tenant_id)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])

def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)

def refresh_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

async def create_refresh_record(db: AsyncSession, user_id, raw_token=None, family_id=None):
    raw_token = raw_token or new_refresh_token()
    record = RefreshToken(
        user_id=user_id,
        token_hash=refresh_hash(raw_token),
        family_id=family_id or uuid.uuid4(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(record)
    await db.flush()
    return raw_token, record

async def revoke_family(db: AsyncSession, family_id):
    rows = (await db.execute(select(RefreshToken).where(RefreshToken.family_id == family_id))).scalars().all()
    now = datetime.now(timezone.utc)
    for row in rows:
        if row.revoked_at is None:
            row.revoked_at = now
