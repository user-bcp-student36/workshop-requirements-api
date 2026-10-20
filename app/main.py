from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from app.api.routes import requirements_router, tasks_router
from app.config import AppSettings
from app.repositories.tasks_repository import TasksRepository
from app.services.requirements_service import RequirementsService


def create_app(
    database_path: str | None = None,
    upload_dir: str | None = None,
    *,
    settings: AppSettings | None = None,
) -> FastAPI:
    """
    Factory de aplicación.

    Cambios relevantes:
    - No ejecuta seed automático incondicional.
    - Requiere configuración JWT segura vía AppSettings/environment.
    - Permite overrides explícitos de paths para despliegues o tests controlados.
    """

    app_settings = settings or AppSettings()

    overrides: dict[str, str] = {}
    if database_path is not None:
        overrides["database_path"] = database_path
    if upload_dir is not None:
        overrides["upload_dir"] = upload_dir

    if overrides:
        app_settings = app_settings.model_copy(update=overrides)

    database_file = Path(app_settings.database_path)
    if database_file.parent != Path("."):
        database_file.parent.mkdir(parents=True, exist_ok=True)

    app_settings.upload_path.mkdir(parents=True, exist_ok=True)

    app = FastAPI(
        title="BCP Backend Auxiliary API",
        version="1.0.0",
        docs_url="/docs" if app_settings.environment != "production" else None,
        redoc_url="/redoc" if app_settings.environment != "production" else None,
    )

    app.state.settings = app_settings
    app.state.tasks_repository = TasksRepository(app_settings.database_path)
    app.state.requirements_service = RequirementsService(
        upload_dir=app_settings.upload_dir,
        allowed_extensions=app_settings.allowed_upload_extensions,
        max_bytes=app_settings.upload_max_bytes,
    )

    app.include_router(tasks_router)
    app.include_router(requirements_router)

    return app


app = create_app()