"""FastAPI entrypoint.

Run in dev mode (auto-reload, like nodemon):
    uv run fastapi dev app/main.py
"""

from fastapi import FastAPI

from app.api.routes import health
from app.core.config import get_settings


def create_app() -> FastAPI:
    """App factory: builds a fresh app, which keeps tests isolated."""
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", debug=settings.debug)
    app.include_router(health.router)
    return app


app = create_app()
