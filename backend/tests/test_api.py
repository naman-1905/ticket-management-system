import asyncio
import os
import uuid

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.main import app
from app.db import Base, get_db
from app.models import Tenant, User
from app.security import hash_password
from app.services.tenancy import seed_permissions, create_tenant_with_owner, ensure_default_sla_policies

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://naman:naman@localhost:5432/ticketing_db_test",
)


def _test_db_reachable(url: str) -> bool:
    """Best-effort connectivity probe so the API tests can be gated on a real DB.

    When no test database is reachable (e.g. an environment without Postgres),
    the whole module is skipped cleanly instead of erroring out in fixture setup.
    """
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
        # Already inside a running event loop; assume available and proceed.
        return True


if not _test_db_reachable(TEST_DATABASE_URL):
    pytest.skip(
        "TEST_DATABASE_URL is not reachable; skipping API integration tests",
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


@pytest.mark.asyncio
async def test_health(client):
    ac, _ = client
    res = await ac.get("/healthz")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_error_envelope_on_404(client):
    ac, _ = client
    res = await ac.get("/api/v1/tickets/00000000-0000-0000-0000-000000000001")
    assert res.status_code == 401
    body = res.json()
    assert "error" in body
    assert "code" in body["error"]


@pytest.mark.asyncio
async def test_users_no_password_hash(client, db_session):
    ac, user = client
    from app.security import create_access_token

    token = create_access_token(user.id, user.role, user.tenant_id)
    res = await ac.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert "password_hash" not in data[0]


@pytest.mark.asyncio
async def test_register_creates_tenant(client):
    ac, _ = client
    email = f"new-{uuid.uuid4().hex[:8]}@test.com"
    res = await ac.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "New User", "password": "password123", "tenant_name": "Acme"},
    )
    assert res.status_code == 201
    tokens = res.json()
    me = await ac.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
    body = me.json()
    assert body["tenant_name"] == "Acme"
    assert "permissions" in body


def _auth(user):
    from app.security import create_access_token

    token = create_access_token(user.id, user.role, user.tenant_id)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_ticket_list_search_by_query(client):
    ac, user = client
    H = _auth(user)
    unique_a = f"alpha{uuid.uuid4().hex[:8]}"
    unique_b = f"bravo{uuid.uuid4().hex[:8]}"

    r1 = await ac.post("/api/v1/tickets", json={"title": f"Ticket {unique_a}", "description": "desc"}, headers=H)
    assert r1.status_code == 201
    r2 = await ac.post("/api/v1/tickets", json={"title": f"Ticket {unique_b}", "description": "desc"}, headers=H)
    assert r2.status_code == 201

    res = await ac.get(f"/api/v1/tickets?q={unique_a}", headers=H)
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert any(unique_a in t["title"] for t in body["items"])

    res_none = await ac.get(f"/api/v1/tickets?q=zzz{uuid.uuid4().hex[:8]}", headers=H)
    assert res_none.status_code == 200
    assert res_none.json()["total"] == 0


@pytest.mark.asyncio
async def test_search_endpoint_matches_ticket_number(client):
    ac, user = client
    H = _auth(user)
    r = await ac.post("/api/v1/tickets", json={"title": "Searchable ticket", "description": "desc"}, headers=H)
    assert r.status_code == 201
    tnum = r.json()["ticket_number"]

    res = await ac.get(f"/api/v1/search/tickets?q={tnum}", headers=H)
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 1
    assert any(t["ticket_number"] == tnum for t in body["items"])


@pytest.mark.asyncio
async def test_csat_flow(client, db_session):
    from sqlalchemy import select

    from app.models import Ticket

    ac, user = client
    session, _ = db_session
    H = _auth(user)

    r = await ac.post("/api/v1/tickets", json={"title": "CSAT ticket", "description": "desc"}, headers=H)
    assert r.status_code == 201
    tid = r.json()["id"]

    # Not resolved yet -> rejected.
    res = await ac.post(f"/api/v1/csat/tickets/{tid}", json={"score": 5}, headers=H)
    assert res.status_code == 400

    # Mark resolved, then submit.
    ticket = (await session.execute(select(Ticket).where(Ticket.id == uuid.UUID(tid)))).scalar_one()
    ticket.status = "RESOLVED"
    await session.commit()

    res = await ac.post(f"/api/v1/csat/tickets/{tid}", json={"score": 4, "comment": "Great"}, headers=H)
    assert res.status_code == 201
    assert res.json()["score"] == 4

    # Existing rating is readable via GET.
    g = await ac.get(f"/api/v1/csat/tickets/{tid}", headers=H)
    assert g.status_code == 200
    assert g.json()["score"] == 4
    assert g.json()["comment"] == "Great"

    # Duplicate submission -> conflict.
    res = await ac.post(f"/api/v1/csat/tickets/{tid}", json={"score": 5}, headers=H)
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_macro_create_and_list(client):
    ac, user = client
    H = _auth(user)
    name = f"macro{uuid.uuid4().hex[:8]}"

    r = await ac.post("/api/v1/macros", json={"name": name, "reply_body": "Thanks for reaching out."}, headers=H)
    assert r.status_code == 201
    macro = r.json()
    assert macro["name"] == name
    assert macro["reply_body"] == "Thanks for reaching out."

    res = await ac.get("/api/v1/macros", headers=H)
    assert res.status_code == 200
    assert any(m["id"] == macro["id"] for m in res.json())


@pytest.mark.asyncio
async def test_organization_and_contact_creation(client):
    ac, user = client
    H = _auth(user)
    org_name = f"Org{uuid.uuid4().hex[:8]}"

    r = await ac.post("/api/v1/organizations", json={"name": org_name, "org_type": "customer"}, headers=H)
    assert r.status_code == 201
    org = r.json()
    assert org["name"] == org_name
    assert org["org_type"] == "customer"

    # Duplicate org name -> conflict.
    dup = await ac.post("/api/v1/organizations", json={"name": org_name, "org_type": "partner"}, headers=H)
    assert dup.status_code == 409

    email = f"contact{uuid.uuid4().hex[:8]}@test.com"
    rc = await ac.post(
        "/api/v1/contacts",
        json={"email": email, "full_name": "New Contact", "organization_id": org["id"]},
        headers=H,
    )
    assert rc.status_code == 201
    contact = rc.json()
    assert contact["email"] == email
    assert str(contact["organization_id"]) == org["id"]

    # Reflected in list endpoints.
    ro = await ac.get("/api/v1/organizations", headers=H)
    assert any(o["id"] == org["id"] for o in ro.json())
    rcs = await ac.get("/api/v1/contacts", headers=H)
    assert any(c["id"] == contact["id"] for c in rcs.json())


@pytest.mark.asyncio
async def test_ticket_creation_idempotency(client):
    ac, user = client
    H = _auth(user)
    key = uuid.uuid4().hex

    r1 = await ac.post(
        "/api/v1/tickets",
        json={"title": "Portal ticket", "description": "desc"},
        headers={**H, "Idempotency-Key": key},
    )
    assert r1.status_code == 201
    first = r1.json()

    # Replay with the same idempotency key returns the same ticket.
    r2 = await ac.post(
        "/api/v1/tickets",
        json={"title": "Portal ticket", "description": "desc"},
        headers={**H, "Idempotency-Key": key},
    )
    assert r2.status_code in (200, 201)
    assert r2.json()["id"] == first["id"]
