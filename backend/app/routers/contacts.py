import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Contact, Organization
from ..schemas import ContactIn, ContactOut
from ..deps import require_permissions
from ..services.audit import audit_log
from ..utils import err

router = APIRouter()


@router.get("", response_model=list[ContactOut])
async def list_contacts(user=Depends(require_permissions("contact.manage")), db: AsyncSession = Depends(get_db)):
    return (
        await db.execute(select(Contact).where(Contact.tenant_id == user.tenant_id).order_by(Contact.email))
    ).scalars().all()


@router.post("", response_model=ContactOut, status_code=201)
async def create_contact(
    body: ContactIn,
    user=Depends(require_permissions("contact.manage")),
    db: AsyncSession = Depends(get_db),
):
    if body.organization_id:
        org = (
            await db.execute(
                select(Organization).where(Organization.id == body.organization_id, Organization.tenant_id == user.tenant_id)
            )
        ).scalar_one_or_none()
        if not org:
            err(404, "NOT_FOUND", "Organization not found")
    exists = (
        await db.execute(
            select(Contact).where(Contact.tenant_id == user.tenant_id, Contact.email == body.email.lower())
        )
    ).scalar_one_or_none()
    if exists:
        err(409, "CONFLICT", "Contact already exists")
    contact = Contact(
        tenant_id=user.tenant_id,
        organization_id=body.organization_id,
        email=body.email.lower(),
        full_name=body.full_name,
    )
    db.add(contact)
    await db.flush()
    await audit_log(db, user, "contact.created", "contact", contact.id, new_values={"email": contact.email})
    await db.commit()
    await db.refresh(contact)
    return contact
