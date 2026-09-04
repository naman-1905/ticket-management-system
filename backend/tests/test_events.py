import asyncio
import os
import uuid

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.main import app
from app.db import Base, get_db
from app.models import Tenant, User, Ticket, OutboxEvent, EventDelivery, Notification
from app.security import hash_password
from app.services.tenancy import seed_permissions, create_tenant_with_owner, ensure_default_sla_policies
from app.services.events import emit_event, relay_events, register_consumer, CONSUMERS, MAX_DELIVERY_ATTEMPTS

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://naman:naman@localhost:5432/ticketing_db_test",
)


def _test_db_reachable(url: str) -> bool:
    dsn = url.replace("+asyncpg", "")

    async def _probe() -> bool:
        try:
            conn = await asyncio.wait_for(asyncpg.connect(dsn=dsn), timeout=3)
            await conn.close()
            return True
        except Exception:
            return False

    try:
        return asyncio.run(_probe())
    except RuntimeError:
        return True


if not _test_db_reachable(TEST_DATABASE_URL):
    pytest.skip(
        "TEST_DATABASE_URL is not reachable; skipping events integration tests",
        allow_module_level=True,
    )


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        await seed_permissions(session)
        tenant, user, _ = await create_tenant_with_owner(
            session,
            tenant_name="Test Co",
            email="owner@test.com",
            full_name="Owner",
            password_hash=hash_password("password123"),
        )
        await ensure_default_sla_policies(session, tenant.id)
        await session.commit()
        yield session, user
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    session, user = db_session

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, user
    app.dependency_overrides.clear()


def _auth(user):
    from app.security import create_access_token

    token = create_access_token(user.id, user.role, user.tenant_id)
    return {"Authorization": f"Bearer {token}"}


async def _last_event(session, event_type: str, entity_id=None):
    q = select(OutboxEvent).where(OutboxEvent.event_type == event_type)
    if entity_id is not None:
        q = q.where(OutboxEvent.entity_id == entity_id)
    rows = (await session.execute(q.order_by(OutboxEvent.created_at.desc()))).scalars().all()
    return rows[0] if rows else None


@pytest.mark.asyncio
async def test_emit_on_ticket_create(client, db_session):
    ac, user = client
    session, _ = db_session
    H = _auth(user)

    r = await ac.post("/api/v1/tickets", json={"title": "t", "description": "d"}, headers=H)
    assert r.status_code == 201
    tid = uuid.UUID(r.json()["id"])

    ev = await _last_event(session, "ticket.created", tid)
    assert ev is not None
    assert str(ev.payload_json["ticket_id"]) == str(tid)


@pytest.mark.asyncio
async def test_emit_on_status_change(client, db_session):
    ac, user = client
    session, _ = db_session
    H = _auth(user)

    r = await ac.post("/api/v1/tickets", json={"title": "t", "description": "d"}, headers=H)
    assert r.status_code == 201
    tid = uuid.UUID(r.json()["id"])

    ticket = (await session.execute(select(Ticket).where(Ticket.id == tid))).scalar_one()
    from app.services.tickets import transition_ticket

    await transition_ticket(session, user, ticket, "OPEN")
    await session.flush()

    ev = await _last_event(session, "ticket.status_changed", tid)
    assert ev is not None
    assert ev.payload_json["from_status"] == "NEW"
    assert ev.payload_json["to_status"] == "OPEN"


@pytest.mark.asyncio
async def test_relay_delivers_and_marks_published(db_session):
    session, user = db_session

    state = {"ran": 0}

    async def ok_handler(db, event):
        state["ran"] += 1

    register_consumer("ticket.created", "test_ok", ok_handler)
    await emit_event(session, user.tenant_id, "ticket.created", "ticket", None, {"ticket_id": "x", "ticket_number": "TCK-TEST"})
    await session.commit()

    await relay_events(session)

    ev = await _last_event(session, "ticket.created")
    assert ev.published_at is not None
    delivery = (
        await session.execute(select(EventDelivery).where(EventDelivery.consumer_name == "test_ok"))
    ).scalar_one()
    assert delivery.status == "delivered"
    assert state["ran"] == 1


@pytest.mark.asyncio
async def test_relay_schedules_retry_on_failure(db_session):
    session, user = db_session

    async def fail_handler(db, event):
        raise RuntimeError("boom")

    register_consumer("ticket.created", "test_fail_retry", fail_handler)
    await emit_event(session, user.tenant_id, "ticket.created", "ticket", None, {"ticket_id": "x", "ticket_number": "TCK-TEST"})
    await session.commit()

    await relay_events(session)

    delivery = (
        await session.execute(
            select(EventDelivery).where(EventDelivery.consumer_name == "test_fail_retry")
        )
    ).scalar_one()
    assert delivery.attempts == 1
    assert delivery.status == "failed"
    assert delivery.next_attempt_at is not None
    assert delivery.last_error is not None


@pytest.mark.asyncio
async def test_relay_dead_letters_after_max_attempts(db_session):
    session, user = db_session

    async def fail_handler(db, event):
        raise RuntimeError("boom")

    register_consumer("ticket.created", "test_fail_dl", fail_handler)
    await emit_event(session, user.tenant_id, "ticket.created", "ticket", None, {"ticket_id": "x", "ticket_number": "TCK-TEST"})
    await session.commit()

    # First pass creates the delivery and records one failed attempt.
    await relay_events(session)

    delivery = (
        await session.execute(select(EventDelivery).where(EventDelivery.consumer_name == "test_fail_dl"))
    ).scalar_one()
    # Fast-forward to the final attempt so we don't wait out the backoff.
    delivery.attempts = MAX_DELIVERY_ATTEMPTS - 1
    delivery.next_attempt_at = None
    await session.commit()

    await relay_events(session)

    delivery = (
        await session.execute(select(EventDelivery).where(EventDelivery.consumer_name == "test_fail_dl"))
    ).scalar_one()
    assert delivery.status == "dead_letter"
    assert delivery.last_error is not None


@pytest.mark.asyncio
async def test_status_change_consumer_is_idempotent(client, db_session):
    ac, user = client
    session, _ = db_session
    H = _auth(user)

    r = await ac.post("/api/v1/tickets", json={"title": "t", "description": "d"}, headers=H)
    assert r.status_code == 201
    tid = uuid.UUID(r.json()["id"])

    from app.services.event_consumers import register_builtin_consumers

    register_builtin_consumers()
    await emit_event(
        session,
        user.tenant_id,
        "ticket.status_changed",
        "ticket",
        tid,
        {"ticket_id": str(tid), "from_status": "NEW", "to_status": "OPEN"},
    )
    await session.commit()

    ev = await _last_event(session, "ticket.status_changed", tid)
    handler = dict(CONSUMERS["ticket.status_changed"])["ticket_status_notify"]
    await handler(session, ev)
    await session.flush()
    await handler(session, ev)  # redelivery must not duplicate the notification

    count = await session.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.extra_data["event_id"].as_string() == str(ev.id))
    )
    assert count == 1


@pytest.mark.asyncio
async def test_events_and_dead_letter_endpoints(client, db_session):
    ac, user = client
    session, _ = db_session
    H = _auth(user)

    await emit_event(session, user.tenant_id, "ticket.created", "ticket", None, {"ticket_id": "x", "ticket_number": "TCK-TEST"})
    await session.commit()

    res = await ac.get("/api/v1/events", headers=H)
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 1
    assert any(e["event_type"] == "ticket.created" for e in body["items"])

    dl = await ac.get("/api/v1/events/dead-letter", headers=H)
    assert dl.status_code == 200
    assert dl.json()["total"] >= 0


