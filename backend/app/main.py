"""FastAPI application entrypoint — backend foundation (STEP 03).

Covers: structure, config/env, DB connection, startup, health endpoints,
/api/v1 version prefix, error envelope, dev CORS, logging, auth foundation.
"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    secret = (settings.auth_secret or "").strip()
    if not secret or secret.lower() in {"changeme", "change-me", "test"}:
        raise RuntimeError("AUTH_SECRET is not set. Copy .env.example to .env and set a strong random value.")
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
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(documents_router)
    app.include_router(processing_router)
    app.include_router(reviews_router)
    app.include_router(records_router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
