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
@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    if settings.environment == "development":
        try:
            import app.modules.identity.models, app.modules.ticketing.models, app.modules.sla.models, app.modules.audit.models, app.modules.notifications.models
            async with engine.begin() as connection: await connection.run_sync(Base.metadata.create_all)
        except Exception: pass
    yield
    await engine.dispose()
def create_app() -> FastAPI:
    application = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
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
