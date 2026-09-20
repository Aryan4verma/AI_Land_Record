"""Standard error envelope per 10_API_SPECIFICATION section 12.

{"error": {"code": ..., "message": ..., "request_id": ...}}
HTTP statuses follow section 13. Unhandled errors return 500 without
leaking internals; validation errors never echo submitted values.
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .logging_config import get_logger

log = get_logger(__name__)


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def _envelope(request: Request, code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message, "request_id": _request_id(request)}}


async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(_envelope(request, exc.code, exc.message), exc.status)


async def _http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = {
        400: "BAD_REQUEST",
        401: "UNAUTHENTICATED",
        403: "UNAUTHORIZED",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
    }.get(exc.status_code, f"HTTP_{exc.status_code}")
    messages = {
        400: "Bad request.",
        401: "Authentication is required.",
        403: "You are not allowed to perform this action.",
        404: "The requested resource was not found.",
        405: "The requested method is not allowed.",
        409: "The request conflicts with the current state.",
        429: "Too many requests. Try again later.",
    }
    message = messages.get(exc.status_code, "The request could not be completed.")
    return JSONResponse(_envelope(request, code, message), exc.status_code)


async def _validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    parts = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", [])[1:]) or "body"
        parts.append(f"{loc}: {err.get('msg', 'invalid value')}")
    message = "; ".join(parts) or "Invalid request."
    return JSONResponse(_envelope(request, "VALIDATION_ERROR", message), 422)


async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    # Do not serialize exception text or tracebacks: provider/database errors
    # can contain submitted values, URLs, or connection details.
    log.error("unhandled error type=%s", type(exc).__name__)
    return JSONResponse(_envelope(request, "INTERNAL_ERROR", "An unexpected error occurred."), 500)


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(Exception, _unhandled_handler)
