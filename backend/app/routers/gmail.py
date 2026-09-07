"""Gmail sync endpoints: trigger sync, check status, update settings."""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import current_user
from ..models import User, EmailSyncState, SyncedEmail, GoogleToken
from ..services.gmail_sync import sync_and_create_tickets

logger = logging.getLogger(__name__)
router = APIRouter()


class GmailSettingsIn(BaseModel):
    enabled: bool


@router.post("/sync")
async def trigger_sync(
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger an immediate email sync for the current user."""
    # Check if user has Google tokens linked
    gtoken = (
        await db.execute(select(GoogleToken).where(GoogleToken.user_id == user.id))
    ).scalar_one_or_none()
    if not gtoken:
        return {"created": 0, "message": "No Google account linked"}

    created = await sync_and_create_tickets(db, user)
    await db.commit()
    return {"created": created}


@router.get("/status")
async def get_status(
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return Gmail sync status for the current user."""
    sync_state = (
        await db.execute(select(EmailSyncState).where(EmailSyncState.user_id == user.id))
    ).scalar_one_or_none()

    gtoken = (
        await db.execute(select(GoogleToken).where(GoogleToken.user_id == user.id))
    ).scalar_one_or_none()

    email_count = await db.scalar(
        select(func.count()).select_from(SyncedEmail).where(SyncedEmail.user_id == user.id)
    ) or 0

    return {
        "connected": gtoken is not None,
        "enabled": sync_state.enabled if sync_state else False,
        "last_synced_at": sync_state.last_synced_at.isoformat() if sync_state and sync_state.last_synced_at else None,
        "emails_synced": email_count,
    }


@router.patch("/settings")
async def update_settings(
    body: GmailSettingsIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enable or disable auto-sync for the current user."""
    sync_state = (
        await db.execute(select(EmailSyncState).where(EmailSyncState.user_id == user.id))
    ).scalar_one_or_none()

    if not sync_state:
        return {"enabled": body.enabled, "message": "No sync state found"}

    sync_state.enabled = body.enabled
    await db.commit()
    return {"enabled": body.enabled}