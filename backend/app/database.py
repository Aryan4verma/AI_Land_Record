"""Supabase access. Backend uses the service_role key (bypasses RLS by
design — RLS is deny-by-default and RBAC is enforced in the API layer).
The client is created once at startup and stored on app.state so tests
can substitute a fake without touching configuration.
"""
from typing import Any

from fastapi import Request
from supabase import Client, create_client

from .config import get_settings
from .errors import AppError
from .logging_config import get_logger

log = get_logger(__name__)


def init_supabase() -> Client | None:
    settings = get_settings()
    if not settings.supabase_configured:
        return None
    try:
        return create_client(settings.supabase_url, settings.supabase_service_role_key)
    except Exception as exc:
        log.warning("supabase init failed: %s", type(exc).__name__)
        return None


def require_db(request: Request) -> Client:
    client = getattr(request.app.state, "supabase", None)
    if client is None:
        raise AppError(503, "SERVICE_NOT_CONFIGURED", "Database is not configured.")
    return client


def ping_database(client: Any) -> bool:
    try:
        client.table("roles").select("name").limit(1).execute()
        return True
    except Exception as exc:
        log.warning("database ping failed: %s", type(exc).__name__)
        return False
