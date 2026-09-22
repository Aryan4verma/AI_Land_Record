"""FastAPI application entrypoint — backend foundation (STEP 03).

Covers: structure, config/env, DB connection, startup, health endpoints,
/api/v1 version prefix, error envelope, dev CORS, logging, auth foundation.
"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .auth.router import router as auth_router
from .config import get_settings
from .database import init_supabase
from .documents.router import router as documents_router
from .errors import install_error_handlers
from .processing.router import router as processing_router
from .records.router import router as records_router
from .reviews.router import router as reviews_router
from .logging_config import get_logger, setup_logging
from .middleware import RequestIDMiddleware
from .routers.health import router as health_router

log = get_logger(__name__)

_MIN_AUTH_SECRET_LENGTH = 32


def validate_auth_secret(secret: str) -> None:
    """Fail closed when the deployment supplies a weak/default JWT secret."""
    normalized = (secret or "").strip()
    if len(normalized) < _MIN_AUTH_SECRET_LENGTH or normalized.lower() in {"changeme", "change-me", "test"}:
        raise RuntimeError("AUTH_SECRET must be a random value of at least 32 characters.")


def _frontend_dist() -> Path:
    """Resolve the optional production bundle in both local and container layouts."""
    return Path(__file__).resolve().parents[2] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    validate_auth_secret(settings.auth_secret)
    app.state.supabase = init_supabase()
    if app.state.supabase is not None:
        from .processing.stores import SupabaseJobStore

        try:
            stale = SupabaseJobStore(app.state.supabase).mark_stale_failed()
            if stale:
                log.info("reconciled %d stale processing job(s)", stale)
        except Exception:
            log.warning("stale job reconciliation failed")
    log.info(
        "startup app=%s version=%s env=%s db=%s",
        settings.app_name,
        settings.app_version,
        settings.environment,
        "configured" if app.state.supabase is not None else "not-configured",
    )
    yield
    log.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level)
    app = FastAPI(title="Land Record Digitization API", version=settings.app_version, lifespan=lifespan)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Accept", "Authorization", "Content-Type"],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )
    install_error_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(documents_router)
    app.include_router(processing_router)
    app.include_router(reviews_router)
    app.include_router(records_router)

    # The Vercel container is intentionally same-origin: FastAPI serves the
    # built Vite bundle and keeps all /api routes behind the existing auth/RBAC
    # boundary. Only install this fallback when a production build is present,
    # so the backend remains usable on its own during local development/tests.
    frontend_dist = _frontend_dist()
    frontend_index = frontend_dist / "index.html"
    if frontend_index.is_file():
        assets_dir = frontend_dist / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def serve_frontend(full_path: str, request: Request):
            if full_path == "api" or full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="Not found")
            root = frontend_dist.resolve()
            requested = (root / full_path).resolve()
            if requested != root and root not in requested.parents:
                raise HTTPException(status_code=404, detail="Not found")
            if requested.is_file():
                return FileResponse(requested)
            # Preserve the backend's 404 contract for API/CLI clients. A
            # browser navigation advertises HTML and receives the SPA shell.
            if full_path and "text/html" not in request.headers.get("accept", ""):
                raise HTTPException(status_code=404, detail="Not found")
            return FileResponse(frontend_index)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
