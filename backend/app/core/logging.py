import time, uuid
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars
class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())); request.state.request_id = request_id; clear_contextvars(); bind_contextvars(request_id=request_id); started = time.perf_counter(); response = await call_next(request)
        response.headers["X-Request-ID"] = request_id; response.headers["X-Response-Time-Ms"] = str(round((time.perf_counter()-started)*1000, 2)); return response
def configure_logging():
    import structlog
    structlog.configure(processors=[structlog.contextvars.merge_contextvars, structlog.processors.TimeStamper(fmt="iso"), structlog.processors.JSONRenderer()])
