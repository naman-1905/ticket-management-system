"""Gmail sync service: fetch emails, parse via LLM, create tickets."""

import base64
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import User, GoogleToken, EmailSyncState, SyncedEmail
from .tickets import create_ticket

logger = logging.getLogger(__name__)


def _get_gmail_service(access_token: str):
    """Create a Gmail API service client."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    credentials = Credentials(token=access_token)
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


async def refresh_google_token(db: AsyncSession, user_id: uuid.UUID) -> str | None:
    """Refresh an expired Google access token. Returns new access token or None."""
    gtoken = (
        await db.execute(select(GoogleToken).where(GoogleToken.user_id == user_id))
    ).scalar_one_or_none()
    if not gtoken or not gtoken.refresh_token:
        return None

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "refresh_token": gtoken.refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            gtoken.access_token = data["access_token"]
            if "expires_in" in data:
                gtoken.token_expiry = datetime.now(timezone.utc) + timedelta(
                    seconds=data["expires_in"]
                )
            await db.flush()
            return gtoken.access_token
    except Exception as exc:
        logger.exception("Failed to refresh Google token for user %s", user_id)
        return None


async def fetch_new_emails(db: AsyncSession, user_id: uuid.UUID) -> list[dict]:
    """Fetch new/unread emails from Gmail. Returns list of email dicts."""
    gtoken = (
        await db.execute(select(GoogleToken).where(GoogleToken.user_id == user_id))
    ).scalar_one_or_none()
    if not gtoken:
        return []

    access_token = gtoken.access_token
    if gtoken.token_expiry and gtoken.token_expiry < datetime.now(timezone.utc):
        access_token = await refresh_google_token(db, user_id)
        if not access_token:
            return []

    service = _get_gmail_service(access_token)

    try:
        results = service.users().messages().list(
            userId="me", q="is:unread newer_than:1d", maxResults=20
        ).execute()
        messages = results.get("messages", [])
    except Exception as exc:
        logger.exception("Gmail API list failed for user %s", user_id)
        return []

    emails = []
    for msg in messages:
        try:
            msg_data = (
                service.users()
                .messages()
                .get(userId="me", messageId=msg["id"], format="raw")
                .execute()
            )
            raw = base64.urlsafe_b64decode(msg_data.get("raw", "")).decode(
                "utf-8", errors="replace"
            )
            subject, sender, body = _parse_email_raw(raw)
            emails.append(
                {
                    "id": msg["id"],
                    "threadId": msg.get("threadId", ""),
                    "subject": subject or "(no subject)",
                    "from": sender or "unknown",
                    "body": body[:5000],
                }
            )
        except Exception as exc:
            logger.warning("Failed to fetch Gmail message %s: %s", msg["id"], exc)



def _parse_email_raw(raw: str) -> tuple[str | None, str | None, str]:
    """Parse subject, from, and body from a raw MIME email string."""
    import email as email_lib
    from email.header import decode_header

    msg = email_lib.message_from_string(raw)
    subject = None
    sender = None

    if msg.get("Subject"):
        subject_parts = decode_header(msg["Subject"])
        subject = "".join(
            part.decode(charset or "utf-8") if isinstance(part, bytes) else part
            for part, charset in subject_parts
        )

    if msg.get("From"):
        sender_parts = decode_header(msg["From"])
        sender = "".join(
            part.decode(charset or "utf-8") if isinstance(part, bytes) else part
            for part, charset in sender_parts
        )

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                charset = part.get_content_charset() or "utf-8"
                body = part.get_payload(decode=True).decode(charset, errors="replace")
                break
    else:
        charset = msg.get_content_charset() or "utf-8"
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode(charset, errors="replace")

    return subject, sender, body


async def parse_email_to_ticket(email_data: dict) -> dict:
    """Call local LLM to extract ticket fields from email data."""
    prompt = (
        "You are a ticket creation assistant. Given the following email, extract:\n"
        "- title (concise summary, max 100 chars)\n"
        "- description (key details, max 500 chars)\n"
        "- priority (P1, P2, P3, or P4)\n"
        "- category (one of: bug, feature_request, question, other)\n\n"
        f"Email Subject: {email_data['subject']}\n"
        f"From: {email_data['from']}\n"
        f"Body: {email_data['body']}\n\n"
        "Respond ONLY in JSON format with keys: title, description, priority, category."
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.llm_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 500,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()

            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]

            result = json.loads(content)
            return {
                "title": result.get("title", email_data["subject"][:100]),
                "description": result.get("description", email_data["body"][:500]),
                "priority": result.get("priority", "P3"),
                "category": result.get("category", "other"),
            }
    except json.JSONDecodeError:
        return {
            "title": email_data["subject"][:100],
            "description": email_data["body"][:500],
            "priority": "P3",
            "category": "other",
        }
    except Exception as exc:
        logger.warning("LLM call failed, using fallback: %s", exc)
        return {
            "title": email_data["subject"][:100],
            "description": email_data["body"][:500],
            "priority": "P3",
            "category": "other",
        }


async def sync_and_create_tickets(db: AsyncSession, user: User) -> int:
    """Orchestrator: fetch emails → for each unprocessed email → call LLM → create ticket.
    Returns the number of tickets created."""
    sync_state = (
        await db.execute(select(EmailSyncState).where(EmailSyncState.user_id == user.id))
    ).scalar_one_or_none()

    if not sync_state or not sync_state.enabled:
        return 0

    emails = await fetch_new_emails(db, user.id)
    if not emails:
        if sync_state:
            sync_state.last_synced_at = datetime.now(timezone.utc)
        return 0

    created_count = 0
    for email_data in emails:
        existing = (
            await db.execute(
                select(SyncedEmail).where(
                    SyncedEmail.user_id == user.id,
                    SyncedEmail.gmail_message_id == email_data["id"],
                )
            )
        ).scalar_one_or_none()
        if existing:
            continue

        ticket_fields = await parse_email_to_ticket(email_data)

        try:
            ticket = await create_ticket(
                db,
                user,
                title=ticket_fields["title"],
                description=(
                    f"[From email from {email_data['from']}]\n\n"
                    f"{ticket_fields['description']}"
                ),
                priority=ticket_fields.get("priority", "P3"),
                category=ticket_fields.get("category"),
                source="EMAIL",
            )
            created_count += 1

            db.add(
                SyncedEmail(
                    user_id=user.id,
                    tenant_id=user.tenant_id,
                    gmail_message_id=email_data["id"],
                    ticket_id=ticket.id,
                    subject=email_data["subject"][:500],
                    sender=email_data["from"][:320],
                    received_at=datetime.now(timezone.utc),
                    processed_at=datetime.now(timezone.utc),
                )
            )
        except Exception as exc:
            logger.warning(
                "Failed to create ticket from email %s: %s", email_data["id"], exc
            )

    if sync_state:
        sync_state.last_synced_at = datetime.now(timezone.utc)
    await db.flush()

    return created_count