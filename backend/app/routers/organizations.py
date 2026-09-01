import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Organization
from ..schemas import OrganizationIn, OrganizationOut
from ..deps import require_permissions
from ..services.audit import audit_log
from ..utils import err

router = APIRouter()


@router.get("", response_model=list[OrganizationOut])
async def list_orgs(user=Depends(require_permissions("organization.manage")), db: AsyncSession = Depends(get_db)):
    return (
        await db.execute(
            select(Organization).where(Organization.tenant_id == user.tenant_id).order_by(Organization.name)
        )
    ).scalars().all()


@router.post("", response_model=OrganizationOut, status_code=201)
async def create_org(
    body: OrganizationIn,
    user=Depends(require_permissions("organization.manage")),
    db: AsyncSession = Depends(get_db),
):
    exists = (
        await db.execute(
            select(Organization).where(Organization.tenant_id == user.tenant_id, Organization.name == body.name)
        )
    ).scalar_one_or_none()
    if exists:
        err(409, "CONFLICT", "Organization already exists")
    org = Organization(tenant_id=user.tenant_id, name=body.name, org_type=body.org_type)
    db.add(org)
    await db.flush()
    await audit_log(db, user, "organization.created", "organization", org.id, new_values={"name": org.name})
    await db.commit()
    await db.refresh(org)
    return org
