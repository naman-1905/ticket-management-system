import logging
import time
import uuid

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text, select

from .config import settings
from .core.errors import http_exception_handler, validation_exception_handler, unhandled_exception_handler
from .core.logging_config import setup_logging
from .db import engine
from .models import WorkerHeartbeat
from .routers import (
    auth,
    users,
    tickets,
    projects,
    sla,
    audit,
    organizations,
    contacts,
    teams,
    notifications,
    search,
    reports,
    kb,
    csat,
    attachments,
    automations,
    events,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Starting API v%s", settings.app_version)
    yield
    await engine.dispose()


app = FastAPI(
    title="Service Desk Platform API",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(Exception, unhandled_exception_handler)
from fastapi import HTTPException

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    logger.info(
        "request method=%s path=%s status=%s latency_ms=%.1f request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - start) * 1000,
        request.state.request_id,
    )
    return response


@app.get("/")
async def root():
    return {"message": "Service Desk Platform API is running"}


async def db_state():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "up"
    except Exception:
        return "down"


@app.get("/healthz")
@app.get("/health")
async def health():
    return {"status": "ok", "db": await db_state()}


@app.get("/readyz")
async def ready():
    db_ok = await db_state() == "up"
    worker_ok = False
    try:
        async with engine.connect() as conn:
            from sqlalchemy.ext.asyncio import AsyncSession
            from .db import SessionLocal

            async with SessionLocal() as session:
                hb = (
                    await session.execute(select(WorkerHeartbeat).order_by(WorkerHeartbeat.last_seen_at.desc()).limit(1))
                ).scalar_one_or_none()
                if hb:
                    from datetime import datetime, timezone, timedelta

                    worker_ok = (datetime.now(timezone.utc) - hb.last_seen_at) < timedelta(minutes=5)
    except Exception:
        worker_ok = False
    status = "ready" if db_ok else "not_ready"
    return {"status": status, "db": "up" if db_ok else "down", "worker": "up" if worker_ok else "unknown"}


@app.get("/api/v1/meta/version")
async def version():
    return {"version": settings.app_version, "git_sha": "unknown"}


app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(tickets.router, prefix="/api/v1/tickets", tags=["tickets"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(sla.router, prefix="/api/v1", tags=["sla"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["audit"])
app.include_router(organizations.router, prefix="/api/v1/organizations", tags=["organizations"])
app.include_router(contacts.router, prefix="/api/v1/contacts", tags=["contacts"])
app.include_router(teams.router, prefix="/api/v1", tags=["teams"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(kb.router, prefix="/api/v1/kb", tags=["kb"])
app.include_router(csat.router, prefix="/api/v1/csat", tags=["csat"])
app.include_router(attachments.router, prefix="/api/v1/attachments", tags=["attachments"])
app.include_router(automations.router, prefix="/api/v1", tags=["automations"])
app.include_router(events.router, prefix="/api/v1", tags=["events"])
