"""FastAPI application factory and lifespan wiring."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI

from vivecaribe import __version__
from vivecaribe.api import deps
from vivecaribe.api.routers import auth, automation, health, reservas
from vivecaribe.logging import configure_logging, logger
from vivecaribe.settings import get_settings


def _init_sentry() -> None:
    """Init Sentry before the FastAPI app is created (errors, traces, logs).

    FastAPI/Starlette integrations are auto-enabled by the SDK. Stdlib
    ``logging`` is bridged when ``enable_logs=True``.
    """
    settings = get_settings()
    if not settings.sentry_dsn:
        return

    # Sample all traces outside prod; keep prod cheaper.
    # traces_sample_rate = 1.0 if settings.environment != "prod" else 0.2
    traces_sample_rate = 1.0

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        release=f"vivecaribe@{__version__}",
        send_default_pii=False,
        traces_sample_rate=traces_sample_rate,
        enable_logs=True,
    )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Configure logging and DB on startup; dispose engine on shutdown."""
    settings = get_settings()
    configure_logging(settings)
    deps.init_db()
    logger.info(
        f"ViveCaribe starting (env={settings.environment}, version={__version__})",
    )
    yield
    await deps.shutdown_db()
    logger.info("ViveCaribe shutting down")


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    # Must run before FastAPI() so request tracing attaches correctly.
    _init_sentry()

    app = FastAPI(
        title="ViveCaribe",
        version=__version__,
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(automation.router)
    app.include_router(reservas.router)
    return app


app = create_app()
