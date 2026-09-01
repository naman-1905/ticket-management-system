import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AuditLog, Contact, Organization, SLAPolicy, Ticket, User
from ..schemas import AuditLogOut


def _user_label(user: User) -> str:
    return user.full_name or user.email


async def audit_log(
    db: AsyncSession,
    user: User | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    old_values: dict | None = None,
    new_values: dict | None = None,
    correlation_id: str | None = None,
):
    db.add(
        AuditLog(
            tenant_id=user.tenant_id if user else None,
            actor_id=user.id if user else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values or {},
            new_values=new_values or {},
            correlation_id=correlation_id,
        )
    )


async def serialize_audit_logs(db: AsyncSession, rows: list[AuditLog]) -> list[AuditLogOut]:
    if not rows:
        return []

    user_ids: set[uuid.UUID] = set()
    ticket_ids: set[uuid.UUID] = set()
    contact_ids: set[uuid.UUID] = set()
    org_ids: set[uuid.UUID] = set()
    sla_ids: set[uuid.UUID] = set()

    for row in rows:
        if row.actor_id:
            user_ids.add(row.actor_id)
        if not row.entity_id:
            continue
        if row.entity_type == "user":
            user_ids.add(row.entity_id)
        elif row.entity_type == "ticket":
            ticket_ids.add(row.entity_id)
        elif row.entity_type == "contact":
            contact_ids.add(row.entity_id)
        elif row.entity_type == "organization":
            org_ids.add(row.entity_id)
        elif row.entity_type == "sla_policy":
            sla_ids.add(row.entity_id)

    users: dict[uuid.UUID, str] = {}
    if user_ids:
        for user in (await db.execute(select(User).where(User.id.in_(user_ids)))).scalars():
            users[user.id] = _user_label(user)

    tickets: dict[uuid.UUID, str] = {}
    if ticket_ids:
        for ticket in (await db.execute(select(Ticket).where(Ticket.id.in_(ticket_ids)))).scalars():
            tickets[ticket.id] = ticket.ticket_number

    contacts: dict[uuid.UUID, str] = {}
    if contact_ids:
        for contact in (await db.execute(select(Contact).where(Contact.id.in_(contact_ids)))).scalars():
            contacts[contact.id] = contact.full_name or contact.email

    organizations: dict[uuid.UUID, str] = {}
    if org_ids:
        for org in (await db.execute(select(Organization).where(Organization.id.in_(org_ids)))).scalars():
            organizations[org.id] = org.name

    sla_policies: dict[uuid.UUID, str] = {}
    if sla_ids:
        for policy in (await db.execute(select(SLAPolicy).where(SLAPolicy.id.in_(sla_ids)))).scalars():
            sla_policies[policy.id] = policy.name

    def entity_name(row: AuditLog) -> str | None:
        if not row.entity_id:
            return None
        lookup: dict[uuid.UUID, str] | None = None
        if row.entity_type == "user":
            lookup = users
        elif row.entity_type == "ticket":
            lookup = tickets
        elif row.entity_type == "contact":
            lookup = contacts
        elif row.entity_type == "organization":
            lookup = organizations
        elif row.entity_type == "sla_policy":
            lookup = sla_policies
        if lookup is None:
            return None
        return lookup.get(row.entity_id)

    return [
        AuditLogOut(
            id=row.id,
            actor_id=row.actor_id,
            actor_name=users.get(row.actor_id) if row.actor_id else None,
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            entity_name=entity_name(row),
            old_values=row.old_values,
            new_values=row.new_values,
            correlation_id=row.correlation_id,
            created_at=row.created_at,
        )
        for row in rows
    ]
