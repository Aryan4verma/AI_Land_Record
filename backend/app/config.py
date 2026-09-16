"""Central configuration. All secrets come from environment variables only."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env_file() -> str | None:
    here = Path(__file__).resolve().parent  # backend/app
    for candidate in (Path.cwd() / ".env", here.parent / ".env", here.parent.parent / ".env"):
        if candidate.is_file():
            return str(candidate)
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_find_env_file(), extra="ignore")

    app_name: str = "Land Records API"
    app_version: str = "0.1.0"
    environment: str = "development"  # development | testing | production
    log_level: str = "INFO"

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    auth_secret: str = ""
    auth_token_expire_minutes: int = 480

    frontend_origins: str = "http://localhost:5173"

    storage_bucket: str = "land-record-documents"
    max_upload_mb: int = 10

    ai_provider: str = "gemini"
    ai_model: str = "gemini-2.0-flash"
    ai_timeout_seconds: int = 60
    gemini_api_key: str = ""
    openrouter_api_key: str = ""
    # Comma-separated "provider:model" fallback routes, e.g.
    # "gemini:gemini-2.0-flash,openrouter:meta-llama/llama-3.3-70b-instruct".
    ai_fallbacks: str = ""
    ai_cache_enabled: bool = True
    ai_cache_ttl_seconds: int = 3600
    ai_cache_max_entries: int = 256

    # Login abuse protection: failed attempts per (client, email) window.
    login_max_attempts: int = 10
    login_window_seconds: int = 300

    # Demo Mode: a controlled demonstration path for known documents that
    # replays precomputed OCR/extraction instead of calling an external
    # provider. Server-side switch — the frontend cannot enable it.
    demo_mode: bool = False
    demo_fixture_directory: str = ""  # blank -> <repo>/demo/fixtures

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def frontend_origin_list(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
