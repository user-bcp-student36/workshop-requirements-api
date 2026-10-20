from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.config import Settings
from app.db import initialize_database
from app.models import HealthResponse
from app.routers import tasks, uploads


def create_app(
    db_path: str | Path | None = None,
    upload_dir: str | Path | None = None,
    *,
    settings: Settings | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings.from_env(db_path=db_path, upload_dir=upload_dir)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = resolved_settings
        initialize_database(resolved_settings.db_path)
        resolved_settings.upload_dir.mkdir(parents=True, exist_ok=True)
        yield

    app = FastAPI(
        title="Workshop Requirements API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings

    app.include_router(tasks.router, prefix="/api")
    app.include_router(uploads.router, prefix="/api")

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    return app


app = create_app()