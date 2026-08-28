from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging import RequestIdMiddleware, configure_logging
from app.db.database import engine, ping_db
from app.db.base import Base
from app.modules.identity.routes import router as auth_router
from app.modules.identity.user_routes import router as users_router
from app.modules.ticketing.routes import router as tickets_router
from app.modules.sla.routes import router as sla_router
from app.modules.audit.routes import router as audit_router
from app.modules.sla.worker import sla_worker
from prometheus_fastapi_instrumentator import Instrumentator
from urllib.parse import urlsplit

async def report_dependency_connections():
    """Print non-secret dependency status so local and deployment startup is diagnosable."""
    db_ok = await ping_db()
    print(f"[connections] PostgreSQL {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db} -> {'CONNECTED' if db_ok else 'UNAVAILABLE'}", flush=True)
    try:
        from redis.asyncio import from_url
        client = from_url(settings.redis_url, decode_responses=True)
        try:
            await __import__("asyncio").wait_for(client.ping(), timeout=3)
            redis_ok = True
        finally:
            await client.aclose()
    except Exception:
        redis_ok = False
    redis_target = urlsplit(settings.redis_url)
    print(f"[connections] Redis {redis_target.hostname or 'configured-host'}:{redis_target.port or 6379} -> {'CONNECTED' if redis_ok else 'UNAVAILABLE'}", flush=True)
    try:
        import aio_pika
        connection = await __import__("asyncio").wait_for(aio_pika.connect_robust(settings.rabbitmq_url), timeout=3)
        await connection.close()
        rabbit_ok = True
    except Exception:
        rabbit_ok = False
    rabbit_target = urlsplit(settings.rabbitmq_url)
    print(f"[connections] RabbitMQ {rabbit_target.hostname or 'configured-host'}:{rabbit_target.port or 5672} -> {'CONNECTED' if rabbit_ok else 'UNAVAILABLE'}", flush=True)
@asynccontextmanager
async def lifespan(application: FastAPI):
    configure_logging()
    await report_dependency_connections()
    if settings.environment == "development":
        try:
            import app.modules.identity.models, app.modules.ticketing.models, app.modules.sla.models, app.modules.audit.models, app.modules.notifications.models
            async with engine.begin() as connection: await connection.run_sync(Base.metadata.create_all)
        except Exception:
            # Local development may start before Postgres; healthz reports the dependency state.
            if settings.environment not in {"development", "test"}: raise
    stop_event = __import__("asyncio").Event(); application.state.stop_event = stop_event
    worker = __import__("asyncio").create_task(sla_worker(stop_event)); application.state.sla_worker = worker
    yield
    stop_event.set(); worker.cancel(); await __import__("asyncio").gather(worker, return_exceptions=True)
    await engine.dispose()
def create_app() -> FastAPI:
    application = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
    Instrumentator().instrument(application).expose(application, include_in_schema=False)
    application.add_middleware(RequestIdMiddleware); application.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"]); register_exception_handlers(application)
    application.include_router(auth_router, prefix="/api/v1"); application.include_router(users_router, prefix="/api/v1"); application.include_router(tickets_router, prefix="/api/v1"); application.include_router(sla_router, prefix="/api/v1"); application.include_router(audit_router, prefix="/api/v1")
    @application.get("/")
    async def root(): return {"message":"Ticket Management System Backend is running"}
    @application.get("/healthz")
    async def healthz(): return {"status":"ok","db":"up" if await ping_db() else "down"}
    @application.get("/health")
    async def health(): return await healthz()
    @application.get("/health/db")
    async def health_db(): return {"status":"healthy" if await ping_db() else "unhealthy"}
    @application.get("/api/v1/meta/version")
    async def version(): return {"version":settings.app_version,"git_sha":"unknown"}
    return application
app = create_app()
