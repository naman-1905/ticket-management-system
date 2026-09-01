from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ..config import settings


def _apply_cors_headers(request: Request, response: JSONResponse) -> JSONResponse:
    origin = request.headers.get("origin")
    if origin and origin in settings.cors_origin_list:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
    return response


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict | None = None,
    request_id: str | None = None,
    request: Request | None = None,
):
    response = JSONResponse(
        status_code=status_code,
        content={
            "error": {"code": code, "message": message, "details": details or {}},
            "request_id": request_id,
        },
    )
    if request is not None:
        _apply_cors_headers(request, response)
    return response


def raise_api_error(status_code: int, code: str, message: str, details: dict | None = None):
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message, "details": details or {}},
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", None)
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        return error_response(
            exc.status_code, detail["code"], detail.get("message", ""), detail.get("details", {}), request_id, request
        )
    return error_response(exc.status_code, "HTTP_ERROR", str(detail), {}, request_id, request)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", None)
    return error_response(
        422,
        "VALIDATION_ERROR",
        "Request validation failed",
        {"fields": exc.errors()},
        request_id,
        request,
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    return error_response(500, "INTERNAL_ERROR", "Unhandled server error", {}, request_id, request)
