import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Attachment
from ..schemas import AttachmentOut
from ..deps import current_user
from ..services.tickets import get_ticket_for_user
from ..storage.local import LocalStorage

router = APIRouter()
storage = LocalStorage()
MAX_SIZE = 10 * 1024 * 1024


@router.post("/tickets/{ticket_id}", response_model=AttachmentOut, status_code=201)
async def upload_attachment(
    ticket_id: uuid.UUID,
    file: UploadFile = File(...),
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await get_ticket_for_user(db, ticket_id, user)
    data = await file.read()
    if len(data) > MAX_SIZE:
        from ..utils import err

        err(400, "VALIDATION_ERROR", "File too large")
    key, checksum = storage.save(user.tenant_id, file.filename or "upload", data)
    att = Attachment(
        tenant_id=user.tenant_id,
        ticket_id=ticket.id,
        uploaded_by=user.id,
        filename=file.filename or "upload",
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=len(data),
        checksum=checksum,
        storage_key=key,
    )
    db.add(att)
    await db.commit()
    await db.refresh(att)
    return att


@router.get("/tickets/{ticket_id}", response_model=list[AttachmentOut])
async def list_attachments(ticket_id: uuid.UUID, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    ticket = await get_ticket_for_user(db, ticket_id, user)
    return (
        await db.execute(select(Attachment).where(Attachment.ticket_id == ticket.id, Attachment.tenant_id == user.tenant_id))
    ).scalars().all()
