import logging
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, details: dict | None = None): self.code, self.message, self.status_code, self.details = code, message, status_code, details or {}
class NotFoundError(AppError):
    def __init__(self, message="Resource not found"): super().__init__("NOT_FOUND", message, 404)
class ConflictError(AppError):
    def __init__(self, message="Conflict", code="CONFLICT"): super().__init__(code, message, 409)
class ForbiddenError(AppError):
    def __init__(self, message="Forbidden"): super().__init__("FORBIDDEN", message, 403)
class RateLimitError(AppError):
    def __init__(self, message="Too many requests"): super().__init__("RATE_LIMITED", message, 429)
def register_exception_handlers(app):
    async def app_error(request: Request, exc: AppError):
        return JSONResponse({"error": {"code": exc.code, "message": exc.message, "details": exc.details}, "request_id": getattr(request.state, "request_id", None)}, status_code=exc.status_code)
    async def validation(request: Request, exc: RequestValidationError):
        return JSONResponse({"error": {"code": "VALIDATION_ERROR", "message": "Request validation failed", "details": {"fields": exc.errors()}}, "request_id": getattr(request.state, "request_id", None)}, status_code=422)
    async def unexpected(request: Request, exc: Exception):
        logging.getLogger(__name__).exception("unhandled_exception", exc_info=exc)
        return JSONResponse({"error": {"code": "INTERNAL_ERROR", "message": "Internal server error", "details": {}}, "request_id": getattr(request.state, "request_id", None)}, status_code=500)
    app.add_exception_handler(AppError, app_error); app.add_exception_handler(RequestValidationError, validation)
    app.add_exception_handler(Exception, unexpected)
