from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import requirements, summary, tasks
from app.config import AppSettings
from app.database import Database
from app.repositories.tasks_repository import TasksRepository
from app.seed import seed_demo_data


def create_app(
    database_path: str | Path | None = None,
    upload_dir: str | Path | None = None,
    *,
    settings: AppSettings | None = None,
    jwt_secret: str | None = None,
    jwt_issuer: str | None = None,
    jwt_audience: str | None = None,
    seed_demo: bool | None = None,
) -> FastAPI:
    resolved_settings = settings or AppSettings.from_env(
        database_path=database_path,
        upload_dir=upload_dir,
        jwt_secret=jwt_secret,
        jwt_issuer=jwt_issuer,
        jwt_audience=jwt_audience,
        seed_demo_data=seed_demo,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        db = Database(resolved_settings.database_path)
        db.connect()
        db.initialize_schema()

        if resolved_settings.seed_demo_data:
            seed_demo_data(TasksRepository(db))

        app.state.db = db

        try:
            yield
        finally:
            db.close()

    app = FastAPI(
        title="Workshop API",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.state.settings = resolved_settings

    app.include_router(tasks.router, prefix="/api")
    app.include_router(summary.router, prefix="/api")
    app.include_router(requirements.router, prefix="/api")

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        # El contrato del backend exige 400 para errores de validación de entrada.
        return JSONResponse(
            status_code=400,
            content={"detail": exc.errors()},
        )

    return app


app = create_app()