"""Database error classification for the store layer.

Every store used to collapse *every* exception into
``AppError(503, "DATABASE_UNAVAILABLE")``. That reported permanent, caller-
caused faults (an invalid date, a duplicate key) as transient outages, and the
real SQLSTATE was never logged — which is precisely what hid the land_records
``record_date`` persistence bug: Postgres said 22008 (datetime field out of
range) and the pipeline reported "database temporarily unavailable".

Classification (10_API_SPECIFICATION section 13):

    22xxx, 23502, 23514  -> 422  data the database cannot represent/accept
    23505                -> 409  duplicate (unique violation)
    23503                -> 409  missing/conflicting reference (FK violation)
    08/53/57/58xxx       -> 503  connection, resource, operator intervention
    anything else        -> 500  unexpected persistence failure

Diagnostics log only the SQLSTATE, exception type, and operation. Driver
messages are deliberately omitted because they can contain submitted values,
connection details, or provider-specific sensitive context.
"""
from __future__ import annotations

import re
from typing import Any

from .errors import AppError
from .logging_config import get_logger

log = get_logger(__name__)

# SQLSTATE is 5 chars whose class (the first two) is numeric for every
# condition we classify. Anchoring on two leading digits stops ordinary
# words in a driver message — "ERROR" is also five uppercase chars —
# from being mistaken for a code.
_SQLSTATE = re.compile(r"\b(\d{2}[0-9A-Z]{3})\b")
_POSTGREST_CODE = re.compile(r"\b(PGRST\d{3})\b")

# Permanent, caller-caused faults.
_DATA_CLASS = "22"          # data exception: 22008 datetime, 22P02 invalid text, ...
_NOT_NULL = "23502"
_FK_VIOLATION = "23503"
_UNIQUE_VIOLATION = "23505"
_CHECK_VIOLATION = "23514"

# Transient / infrastructure faults.
_UNAVAILABLE_CLASSES = ("08", "53", "57", "58")
_UNAVAILABLE_TYPES = (
    "ConnectError", "ConnectTimeout", "ReadTimeout", "WriteTimeout", "PoolTimeout",
    "TimeoutException", "RemoteProtocolError", "NetworkError", "TransportError",
)


def sqlstate_of(exc: BaseException) -> str | None:
    """Best-effort SQLSTATE extraction from supabase/postgrest/httpx errors."""
    code = getattr(exc, "code", None)
    if isinstance(code, str) and _SQLSTATE.fullmatch(code):
        return code
    for attr in ("pgcode", "sqlstate"):
        value = getattr(exc, attr, None)
        if isinstance(value, str) and _SQLSTATE.fullmatch(value):
            return value
    if isinstance(exc, dict):  # some clients raise dict-like payloads
        value = exc.get("code")
        if isinstance(value, str) and _SQLSTATE.fullmatch(value):
            return value
    # Fall back to the rendered message, e.g. 'ERROR:  22008: ...'
    match = _SQLSTATE.search(str(exc))
    return match.group(1) if match else None


def provider_code_of(exc: BaseException) -> str | None:
    """Extract a safe PostgREST/provider code without retaining its message."""
    code = getattr(exc, "code", None)
    if isinstance(code, str) and _POSTGREST_CODE.fullmatch(code):
        return code
    match = _POSTGREST_CODE.search(str(exc))
    return match.group(1) if match else None


def _is_unavailable(exc: BaseException, state: str | None) -> bool:
    if state and state.startswith(_UNAVAILABLE_CLASSES):
        return True
    if type(exc).__name__ in _UNAVAILABLE_TYPES:
        return True
    text = str(exc).lower()
    return any(
        hint in text
        for hint in ("connection refused", "could not connect", "timed out",
                     "temporarily unavailable", "server closed the connection")
    )


def classify_db_error(exc: BaseException, *, subject: str, action: str) -> AppError:
    """Map a driver exception onto the right AppError, and log the cause.

    `subject` names the store ("Record store"), `action` the operation
    ("create record") — both appear in logs only, never in client output.
    """
    state = sqlstate_of(exc)
    provider_code = provider_code_of(exc)
    log.warning(
        "database error: action=%s sqlstate=%s provider_code=%s type=%s",
        action, state or "unknown", provider_code or "unknown", type(exc).__name__,
    )

    if state and (state.startswith(_DATA_CLASS) or state in (_CHECK_VIOLATION, _NOT_NULL)):
        return AppError(
            422, "INVALID_FIELD_VALUE",
            "A value in this record cannot be stored in the expected format.",
        )
    if state == _UNIQUE_VIOLATION:
        return AppError(409, "ALREADY_EXISTS", "This record already exists.")
    if state == _FK_VIOLATION:
        return AppError(409, "REFERENCE_CONFLICT",
                        "A referenced record is missing or still in use.")
    if _is_unavailable(exc, state):
        return AppError(503, "DATABASE_UNAVAILABLE", f"{subject} is temporarily unavailable.")
    return AppError(500, "PERSISTENCE_FAILED", "The record could not be stored.")


def db_guard(subject: str, action: str):
    """Context manager translating any driver exception via classify_db_error."""

    class _Guard:
        def __enter__(self) -> None:
            return None

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            if exc is None or isinstance(exc, AppError):
                return False
            raise classify_db_error(exc, subject=subject, action=action) from exc

    return _Guard()
