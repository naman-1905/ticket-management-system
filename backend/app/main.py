import uuid, traceback
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from .db import engine, Base
from . import models
from .routers import auth, users, tickets, sla, audit

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app = FastAPI(title="Ticket Management System Backend", version="1.0.0", lifespan=lifespan)

@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response
    except Exception:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={
            "error":{"code":"INTERNAL_ERROR","message":"Unhandled server error","details":{}},
            "request_id":request.state.request_id
        })

@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(status_code=500, content={
        "error":{"code":"INTERNAL_ERROR","message":"Unhandled server error","details":{}},
        "request_id":getattr(request.state,"request_id",str(uuid.uuid4()))
    })

@app.get("/")
async def root():
    return {"message":"Ticket Management System Backend is running"}

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
    return {"status":"ok","db":await db_state()}

@app.get("/health/db")
async def health_db():
    state = await db_state()
    return {"status":"healthy" if state=="up" else "unhealthy"}

@app.get("/api/v1/meta/version")
async def version():
    from .config import settings
    return {"version":settings.app_version,"git_sha":"unknown"}

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(tickets.router, prefix="/api/v1/tickets", tags=["tickets"])
app.include_router(sla.router, prefix="/api/v1", tags=["sla"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["audit"])
