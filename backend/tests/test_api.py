import os
import uuid
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
