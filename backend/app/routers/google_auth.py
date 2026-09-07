"""Google OAuth authentication and token management."""

import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..core.errors import raise_api_error
from ..db import get_db
from ..models import User, GoogleToken, EmailSyncState
from ..schemas import TokenOut
from ..security import create_access_token, create_refresh_record
from ..services.tenancy import (
    create_tenant_with_owner,
    ensure_default_sla_policies,
    seed_permissions,
)

logger = logging.getLogger(__name__)
router = APIRouter()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def _build_google_auth_url() -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def _exchange_code_for_tokens(code: str) -> dict:
    import httpx

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "grant_type": "authorization_code",
                "redirect_uri": settings.google_redirect_uri,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def _decode_id_token(id_token: str) -> dict:
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    verified = google_id_token.verify_oauth2_token(
        id_token, google_requests.Request()
    )
    return verified


@router.get("/google/login")
async def google_login():
    """Return the Google OAuth authorization URL for the frontend to redirect to."""
    if not settings.google_client_id:
        raise_api_error(503, "GOOGLE_OAUTH_NOT_CONFIGURED", "Google OAuth is not configured")
    return {"url": _build_google_auth_url()}


@router.get("/google/callback")
async def google_callback(
    code: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth callback: exchange code, upsert user, store tokens, issue app JWT."""
    if not settings.google_client_id:
        raise_api_error(503, "GOOGLE_OAUTH_NOT_CONFIGURED", "Google OAuth is not configured")

    try:
        token_data = await _exchange_code_for_tokens(code)
    except Exception as exc:
        logger.exception("Google token exchange failed")
        raise_api_error(401, "GOOGLE_AUTH_FAILED", f"Token exchange failed: {exc}")

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    id_token = token_data.get("id_token")
    expires_in = token_data.get("expires_in", 3600)

    if not access_token or not id_token:
        raise_api_error(401, "GOOGLE_AUTH_FAILED", "Missing tokens from Google response")

    try:
        user_info = await _decode_id_token(id_token)
    except Exception as exc:
        logger.exception("ID token verification failed")
        raise_api_error(401, "GOOGLE_AUTH_FAILED", f"ID token verification failed: {exc}")

    email = user_info.get("email", "").lower()
    full_name = user_info.get("name", "") or email.split("@")[0]

    if not email:
        raise_api_error(401, "GOOGLE_AUTH_FAILED", "No email in Google token")

    existing_users = (
        await db.execute(select(User).where(User.email == email))
    ).scalars().all()

    if existing_users:
        user = existing_users[0]
        if not user.is_active:
            raise_api_error(403, "USER_INACTIVE", "User account is inactive")
    else:
        await seed_permissions(db)
        tenant_name = full_name.split()[0].title() + "'s Workspace"
        tenant, user, _contact = await create_tenant_with_owner(
            db,
            tenant_name=tenant_name,
            email=email,
            full_name=full_name,
            password_hash="",
        )
        await ensure_default_sla_policies(db, tenant.id)

    existing_gtoken = (
        await db.execute(select(GoogleToken).where(GoogleToken.user_id == user.id))
    ).scalar_one_or_none()

    token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    if existing_gtoken:
        existing_gtoken.access_token = access_token
        existing_gtoken.refresh_token = refresh_token or existing_gtoken.refresh_token
        existing_gtoken.token_expiry = token_expiry
        existing_gtoken.scopes = " ".join(GOOGLE_SCOPES)
        existing_gtoken.updated_at = datetime.now(timezone.utc)
    else:
        db.add(
            GoogleToken(
                user_id=user.id,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expiry=token_expiry,
                scopes=" ".join(GOOGLE_SCOPES),
            )
        )

    sync_state = (
        await db.execute(select(EmailSyncState).where(EmailSyncState.user_id == user.id))
    ).scalar_one_or_none()
    if not sync_state:
        db.add(
            EmailSyncState(
                user_id=user.id,
                tenant_id=user.tenant_id,
                enabled=True,
            )
        )

    raw_refresh, _rec = await create_refresh_record(db, user.id)
    tokens = TokenOut(
        access_token=create_access_token(user.id, user.role, user.tenant_id),
        refresh_token=raw_refresh,
    )

    await db.commit()
    return tokens