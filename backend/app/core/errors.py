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
def register_exception_handlers(app):
    async def app_error(_: Request, exc: AppError): return JSONResponse(exc.status_code, {"error": {"code": exc.code, "message": exc.message, "details": exc.details}})
    async def validation(_: Request, exc: RequestValidationError): return JSONResponse(422, {"error": {"code": "VALIDATION_ERROR", "message": "Request validation failed", "details": {"fields": exc.errors()}}})
    app.add_exception_handler(AppError, app_error); app.add_exception_handler(RequestValidationError, validation)
