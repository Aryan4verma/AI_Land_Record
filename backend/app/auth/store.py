"""User lookup. SupabaseUserStore reads the users table via the
service_role client; tests substitute an in-memory store through
FastAPI dependency_overrides without touching this code.
"""
from typing import Any, Protocol

from fastapi import Request

from ..database import require_db
from ..db_errors import classify_db_error, sqlstate_of
from ..errors import AppError

_COLUMNS = "id,name,email,password_hash,role,status,id_number"


class UserStore(Protocol):
    def get_by_email(self, email: str) -> dict[str, Any] | None: ...
    def get_by_id(self, user_id: str) -> dict[str, Any] | None: ...
    def create_user(self, row: dict[str, Any]) -> dict[str, Any]: ...


class SupabaseUserStore:
    def __init__(self, client: Any) -> None:
        self.client = client

    def _one(self, column: str, value: str) -> dict[str, Any] | None:
        try:
            result = (
                self.client.table("users").select(_COLUMNS).eq(column, value).limit(1).execute()
            )
        except Exception as exc:
            raise classify_db_error(
                exc, subject="User store", action="auth.lookup") from exc
        rows = result.data or []
        return rows[0] if rows else None

    def get_by_email(self, email: str) -> dict[str, Any] | None:
        return self._one("email", email)

    def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        return self._one("id", user_id)

    def create_user(self, row: dict[str, Any]) -> dict[str, Any]:
        try:
            result = self.client.table("users").insert(row).execute()
        except Exception as exc:
            # Backstop for the pre-check in the router: the UNIQUE(email)
            # constraint wins any insert race with a friendly 409. Every
            # other fault is classified rather than flattened to 503.
            if sqlstate_of(exc) == "23505" or "duplicate" in str(exc).lower():
                raise AppError(409, "USER_EXISTS", "An account with this email already exists.") from exc
            raise classify_db_error(
                exc, subject="User store", action="auth.create_user") from exc
        rows = result.data or []
        if not rows or not rows[0].get("id"):
            raise AppError(503, "DATABASE_UNAVAILABLE", "Account was not created.")
        return rows[0]


def get_user_store(request: Request) -> UserStore:
    return SupabaseUserStore(require_db(request))
