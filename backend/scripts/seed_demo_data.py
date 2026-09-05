"""Seed a demo tenant with realistic tickets for the dashboard/graph showcase.

Run (from backend/):
    python -m scripts.seed_demo_data            # create if missing, else no-op
    python -m scripts.seed_demo_data --reset    # wipe + re-seed the demo tenant

Creates the "Acme Support" tenant and fills it with ~60 tickets spread across
the last 14 days: every status (full donut), P1-P4 priorities, backdated
created/resolved timestamps (realistic area-chart trend + avg resolution time),
some unassigned open tickets, and a handful of breached SLAs.

Frontend showcase login:
    demo@acme.com / Demo1234
"""

import argparse
import asyncio
import random
import uuid as _uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db import engine
from app import models  # noqa: F401  (register all tables)
from app.models import SLAPolicy, SLAPolicyVersion, Ticket, TicketSLA, Tenant, User
from app.security import hash_password
from app.services.tenancy import create_tenant_with_owner, ensure_default_sla_policies

DEMO_TENANT = "Acme Support"
DEMO_EMAIL = "demo@acme.com"
DEMO_PASSWORD = "Demo1234"

OPEN_STATUSES = {"NEW", "OPEN", "IN_PROGRESS", "WAITING_FOR_CUSTOMER", "WAITING_FOR_INTERNAL", "ON_HOLD"}

# (status, weight) — tuned so every status appears in the donut.
STATUS_WEIGHTS = [
    ("RESOLVED", 12),
    ("CLOSED", 9),
    ("IN_PROGRESS", 7),
    ("OPEN", 6),
    ("WAITING_FOR_CUSTOMER", 5),
    ("NEW", 4),
    ("ON_HOLD", 3),
    ("WAITING_FOR_INTERNAL", 2),
    ("CANCELLED", 2),
]
PRIORITY_WEIGHTS = [("P1", 8), ("P2", 16), ("P3", 22), ("P4", 9)]

CATEGORIES = ["Billing", "Technical", "Account", "Shipping", "General"]
SOURCES = ["WEB", "EMAIL", "API", "PHONE"]

TITLES = [
    "Unable to log in after password reset",
    "Payment failed but amount was deducted",
    "Order not delivered within promised time",
    "App crashes when uploading a photo",
    "Invoice PDF shows wrong billing address",
    "Two-factor code never arrives by SMS",
    "Feature request: dark mode for mobile app",
    "Cannot update payment method on account",
    "Search returns no results for valid query",
    "Dashboard charts not loading in Safari",
    "Refund not received after 10 business days",
    "API rate limit hit during normal usage",
    "Password change email link expired instantly",
    "Data export CSV missing columns",
    "Notifications sent to wrong recipient",
    "Subscription renewed but plan still shows old tier",
    "Image preview broken on product page",
    "Cannot invite teammate to workspace",
    "Report download times out for large ranges",
    "Mobile app stuck on splash screen after update",
]

DESCRIPTIONS = [
    "Customer reports the issue started after the latest release. Steps include screenshots and device details.",
    "Reproduced on staging. The request fails with a 500 and no entry in the application logs, only in the gateway.",
    "Multiple customers affected. Priority should be raised if it continues into the next business day.",
    "Customer is on the annual plan and has already been offered a goodwill credit for the inconvenience.",
    "Intermittent issue, occurs roughly once every few sessions. Awaiting additional logs from the reporter.",
    "The customer tried clearing cache and using an incognito window but the problem persists across browsers.",
    "Linked to a recent infrastructure change. Engineering is investigating whether it correlates with the deploy.",
    "Customer provided order number and timestamps. Finance has been looped in for the billing side.",
]


def _weighted(rng, weights):
    total = sum(w for _, w in weights)
    r = rng.randint(1, total)
    acc = 0
    for value, weight in weights:
        acc += weight
        if r <= acc:
            return value
    return weights[-1][0]


async def _reset_demo_tenant(db, tenant_id):
    """Remove demo-tenant tickets/SLAs so --reset can re-seed cleanly."""
    await db.execute(delete(TicketSLA).where(TicketSLA.tenant_id == tenant_id))
    await db.execute(delete(Ticket).where(Ticket.tenant_id == tenant_id))
    policy_ids = (await db.execute(select(SLAPolicy.id).where(SLAPolicy.tenant_id == tenant_id))).scalars().all()
    if policy_ids:
        await db.execute(delete(SLAPolicyVersion).where(SLAPolicyVersion.policy_id.in_(policy_ids)))
        await db.execute(delete(SLAPolicy).where(SLAPolicy.id.in_(policy_ids)))


async def main():
    parser = argparse.ArgumentParser(description="Seed demo tickets for the dashboard showcase")
    parser.add_argument("--reset", action="store_true", help="Wipe and re-seed the demo tenant")
    args = parser.parse_args()

    rng = random.Random(42)  # deterministic distribution
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as db:
        existing = (await db.execute(select(Tenant).where(Tenant.name == DEMO_TENANT))).scalar_one_or_none()

        if existing and not args.reset:
            print(f"Demo tenant '{DEMO_TENANT}' already exists. Re-run with --reset to refresh its data.")
            return

        if existing and args.reset:
            await _reset_demo_tenant(db, existing.id)

        if existing:
            tenant = existing
            owner = (
                await db.execute(select(User).where(User.tenant_id == tenant.id, User.role == "OWNER"))
            ).scalar_one()
        else:
            tenant, owner, _contact = await create_tenant_with_owner(
                db,
                tenant_name=DEMO_TENANT,
                email=DEMO_EMAIL,
                full_name="Demo Owner",
                password_hash=hash_password(DEMO_PASSWORD),
            )

        await ensure_default_sla_policies(db, tenant.id)
        policies = {
            p.priority: p
            for p in (await db.execute(select(SLAPolicy).where(SLAPolicy.tenant_id == tenant.id))).scalars().all()
        }

        now = datetime.now(timezone.utc)
        # created-count per day, index 0 = 13 days ago ... index 13 = today (gentle upward trend).
        day_counts = [2, 3, 3, 4, 3, 5, 4, 6, 5, 4, 6, 5, 7, 6]

        tickets = []
        for days_ago in range(13, -1, -1):
            count = day_counts[13 - days_ago]
            for _ in range(count):
                status = _weighted(rng, STATUS_WEIGHTS)
                priority = _weighted(rng, PRIORITY_WEIGHTS)
                title = rng.choice(TITLES)
                desc = rng.choice(DESCRIPTIONS)

                day_start = (now - timedelta(days=days_ago)).replace(
                    hour=rng.randint(0, 23), minute=rng.randint(0, 59), second=0, microsecond=0
                )
                created_at = min(day_start, now - timedelta(minutes=1))

                resolved_at = closed_at = first_response_at = None
                if status in ("RESOLVED", "CLOSED"):
                    resolved_at = min(created_at + timedelta(hours=rng.uniform(2, 48)), now)
                    first_response_at = created_at + timedelta(minutes=rng.randint(5, 240))
                    if status == "CLOSED":
                        closed_at = min(resolved_at + timedelta(hours=rng.uniform(1, 30)), now)
                elif status in OPEN_STATUSES:
                    first_response_at = (
                        created_at + timedelta(minutes=rng.randint(5, 300)) if rng.random() < 0.7 else None
                    )

                assignee_id = owner.id
                if status in OPEN_STATUSES and rng.random() < 0.35:
                    assignee_id = None  # leave some open tickets unassigned

                tnum = "TCK-" + _uuid.uuid4().hex[:12].upper()
                ticket = Ticket(
                    tenant_id=tenant.id,
                    ticket_number=tnum,
                    title=title,
                    description=desc,
                    status=status,
                    priority=priority,
                    ticket_type="INCIDENT",
                    source=rng.choice(SOURCES),
                    category=rng.choice(CATEGORIES),
                    customer_id=owner.id,
                    assignee_id=assignee_id,
                    created_by=owner.id,
                    custom_fields={},
                    version=1,
                    search_vector=f"{tnum} {title} {desc}".lower(),
                    created_at=created_at,
                    updated_at=min(created_at + timedelta(hours=rng.uniform(0, 24)), now),
                    first_response_at=first_response_at,
                    resolved_at=resolved_at,
                    closed_at=closed_at,
                )
                db.add(ticket)
                tickets.append((ticket, priority))

        await db.flush()

        # Mark a handful of SLAs as breached so the red KPI has data.
        for ticket, priority in rng.sample(tickets, k=min(5, len(tickets))):
            policy = policies.get(priority) or next(iter(policies.values()))
            db.add(
                TicketSLA(
                    tenant_id=tenant.id,
                    ticket_id=ticket.id,
                    policy_id=policy.id,
                    status="BREACHED",
                    first_response_due_at=ticket.created_at + timedelta(minutes=60),
                    resolution_due_at=ticket.created_at + timedelta(hours=24),
                    breached_at=min(ticket.created_at + timedelta(hours=30), now),
                )
            )

        await db.commit()
        print(f"Seeded {len(tickets)} tickets into '{DEMO_TENANT}'.")
        print(f"Frontend login: {DEMO_EMAIL} / {DEMO_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(main())


