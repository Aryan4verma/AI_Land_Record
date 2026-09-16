"""Health endpoints per 13_DEPLOYMENT_RUNBOOK section 11.

GET /health          — liveness, no secrets
GET /health/database — Supabase reachability (503 when not configured)
GET /health/ai       — AI wiring status from live configuration (no secrets)
"""
from fastapi import APIRouter, Depends, Request
from supabase import Client

from ..config import get_settings
from ..database import ping_database, require_db
from ..errors import AppError

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get("/health/database")
def health_database(request: Request, client: Client = Depends(require_db)) -> dict:
    if ping_database(client):
        return {"database": "connected"}
    raise AppError(503, "DATABASE_UNAVAILABLE", "Database is temporarily unavailable.")


@router.get("/health/ai")
def health_ai() -> dict:
    settings = get_settings()
    provider = (settings.ai_provider or "").strip().lower()
    key_attr = {"gemini": "gemini_api_key", "openrouter": "openrouter_api_key"}.get(provider)
    key_present = bool(getattr(settings, key_attr, "") if key_attr else "")
    lanes = 1 + sum(1 for chunk in (settings.ai_fallbacks or "").split(",") if ":" in chunk)
    if not provider or not key_present:
        return {"ai": "not_configured", "detail": "No AI provider key is configured."}
    return {
        "ai": "configured",
        "provider": provider,
        "model": (settings.ai_model or "").strip(),
        "lanes": lanes,
        "cache_enabled": bool(settings.ai_cache_enabled),
        # Capability flag so the UI can hide a selector the server would
        # refuse anyway. The server stays the authority (403 on misuse).
        "demo_enabled": bool(getattr(settings, "demo_mode", False)),
    }
