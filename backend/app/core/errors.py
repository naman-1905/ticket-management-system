from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def error_response(status_code: int, code: str, message: str, details: dict | None = None, request_id: str | None = None):
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {"code": code, "message": message, "details": details or {}},
            "request_id": request_id,
        },
    )


def raise_api_error(status_code: int, code: str, message: str, details: dict | None = None):
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message, "details": details or {}},
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", None)
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        return error_response(exc.status_code, detail["code"], detail.get("message", ""), detail.get("details", {}), request_id)
    return error_response(exc.status_code, "HTTP_ERROR", str(detail), {}, request_id)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", None)
    return error_response(
        422,
        "VALIDATION_ERROR",
        "Request validation failed",
        {"fields": exc.errors()},
        request_id,
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    return error_response(500, "INTERNAL_ERROR", "Unhandled server error", {}, request_id)
