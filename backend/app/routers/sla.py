import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import SLAPolicy, SLAPolicyVersion, TicketSLA
from ..schemas import SLAPolicyIn, SLAPolicyOut, TicketSLAOut
from ..deps import require_permissions, current_user
from ..services.tickets import get_ticket_for_user
from ..services.audit import audit_log
from ..utils import err

router = APIRouter()


@router.get("/sla/policies", response_model=list[SLAPolicyOut])
async def policies(user=Depends(require_permissions("sla.view")), db: AsyncSession = Depends(get_db)):
    return (
        await db.execute(
            select(SLAPolicy)
            .where(SLAPolicy.tenant_id == user.tenant_id, SLAPolicy.is_active == True)  # noqa: E712
            .order_by(SLAPolicy.priority)
        )
    ).scalars().all()


@router.post("/sla/policies", response_model=SLAPolicyOut, status_code=201)
async def create_policy(
    body: SLAPolicyIn,
    user=Depends(require_permissions("sla.manage")),
    db: AsyncSession = Depends(get_db),
):
    exists = (
        await db.execute(
            select(SLAPolicy).where(SLAPolicy.tenant_id == user.tenant_id, SLAPolicy.name == body.name)
        )
    ).scalar_one_or_none()
    if exists:
        err(409, "CONFLICT", "SLA policy name already exists")
    p = SLAPolicy(tenant_id=user.tenant_id, **body.model_dump())
    db.add(p)
    await db.flush()
    db.add(
        SLAPolicyVersion(
            policy_id=p.id,
            version=1,
            first_response_minutes=body.first_response_minutes,
            resolution_hours=body.resolution_hours,
        )
    )
    await audit_log(db, user, "sla.policy_created", "sla_policy", p.id, new_values=body.model_dump())
    await db.commit()
    await db.refresh(p)
    return p


@router.patch("/sla/policies/{policy_id}", response_model=SLAPolicyOut)
async def update_policy(
    policy_id: uuid.UUID,
    body: SLAPolicyIn,
    user=Depends(require_permissions("sla.manage")),
    db: AsyncSession = Depends(get_db),
):
    p = (
        await db.execute(
            select(SLAPolicy).where(SLAPolicy.id == policy_id, SLAPolicy.tenant_id == user.tenant_id)
        )
    ).scalar_one_or_none()
    if not p:
        err(404, "NOT_FOUND", "SLA policy not found")
    p.name = body.name
    p.priority = body.priority
    p.first_response_minutes = body.first_response_minutes
    p.resolution_hours = body.resolution_hours
    p.is_active = body.is_active
    p.updated_at = datetime.now(timezone.utc)
    last_version = (
        await db.execute(
            select(SLAPolicyVersion).where(SLAPolicyVersion.policy_id == p.id).order_by(SLAPolicyVersion.version.desc())
        )
    ).scalars().first()
    next_v = (last_version.version + 1) if last_version else 1
    db.add(
        SLAPolicyVersion(
            policy_id=p.id,
            version=next_v,
            first_response_minutes=body.first_response_minutes,
            resolution_hours=body.resolution_hours,
        )
    )
    await audit_log(db, user, "sla.policy_updated", "sla_policy", p.id, new_values=body.model_dump())
    await db.commit()
    await db.refresh(p)
    return p


@router.delete("/sla/policies/{policy_id}", status_code=204)
async def delete_policy(
    policy_id: uuid.UUID,
    user=Depends(require_permissions("sla.manage")),
    db: AsyncSession = Depends(get_db),
):
    p = (
        await db.execute(
            select(SLAPolicy).where(SLAPolicy.id == policy_id, SLAPolicy.tenant_id == user.tenant_id)
        )
    ).scalar_one_or_none()
    if not p:
        err(404, "NOT_FOUND", "SLA policy not found")
    await audit_log(db, user, "sla.policy_deleted", "sla_policy", p.id, old_values={"name": p.name, "priority": p.priority})
    await db.delete(p)
    await db.commit()


@router.get("/tickets/{ticket_id}/sla", response_model=TicketSLAOut | dict)
async def ticket_sla(ticket_id: uuid.UUID, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    t = await get_ticket_for_user(db, ticket_id, user)
    row = (await db.execute(select(TicketSLA).where(TicketSLA.ticket_id == t.id))).scalar_one_or_none()
    if not row:
        return {"ticket_id": str(t.id), "status": "PENDING"}
    return row
