"""Error-envelope contract and leakage protections."""

import asyncio
import logging

from starlette.requests import Request
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors import _http_error_handler, _unhandled_handler


def test_unknown_route_uses_envelope(client):
    response = client.get("/no-such-route")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "NOT_FOUND"
    assert error["request_id"]


def test_login_validation_error_never_echoes_password(client):
    response = client.post("/api/v1/auth/login", json={"email": "a@b.co"})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "secret" not in body["error"]["message"].lower()


def _request():
    return Request({"type": "http", "method": "GET", "path": "/test", "headers": []})


def test_framework_http_error_detail_is_not_returned(client):
    response = asyncio.run(_http_error_handler(_request(), StarletteHTTPException(400, detail="secret-value")))
    assert response.body and b"secret-value" not in response.body


def test_unhandled_error_does_not_leak_exception_text_or_traceback(caplog):
    secret = "document-sensitive-value"
    with caplog.at_level("ERROR"):
        response = asyncio.run(_unhandled_handler(_request(), RuntimeError(secret)))
    assert secret not in response.body.decode()
    assert secret not in caplog.text
    assert b"INTERNAL_ERROR" in response.body


def test_transport_loggers_do_not_emit_info_urls():
    """Provider query-string credentials must not appear in INFO logs."""
    assert logging.getLogger("httpx").level >= logging.WARNING
    assert logging.getLogger("httpcore").level >= logging.WARNING
