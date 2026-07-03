from __future__ import annotations

from fastapi import FastAPI

from .api import approval_requests, health
from .config import get_settings
from .errors import register_error_handlers
from .logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Service for approving content before publication.",
    )

    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(approval_requests.router)
    return app


app = create_app()
