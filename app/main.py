from __future__ import annotations

import os
import sqlite3
from http import HTTPStatus
from pathlib import Path
from typing import Any

import urllib3
from fastapi import Body, Depends, FastAPI, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth_token import InvalidTokenError, TokenVerifier
from app.models import Identity, Task, TaskCreate, TaskSummary, UploadResult
from app.task_repository import TaskRepository
from app.task_service import TaskService
from app.upload_service import UploadService

TASK_STORAGE_ERROR_DETAIL = "Task storage error"


def token_identity(request: Request, authorization: str = Header(default="")) -> dict[str, str]:
    try:
        return request.app.state.token_verifier.verify(authorization)
    except InvalidTokenError as error:
        raise HTTPException(status_code=401, detail="Invalid token: invalid token") from error


def task_identity(identity: dict[str, str] = Depends(token_identity)) -> Identity:
    return Identity.model_validate(identity)


def create_app(db_path: str | None = None, upload_dir: str | None = None) -> FastAPI:
    selected_db = db_path or os.getenv("WORKSHOP_DB_PATH", "./data/workshop.db")
    selected_uploads = upload_dir or os.getenv("WORKSHOP_UPLOAD_DIR", "./uploads")
    Path(selected_db).parent.mkdir(parents=True, exist_ok=True)
    Path(selected_uploads).mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(selected_db, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT NOT NULL, status TEXT NOT NULL, owner TEXT NOT NULL, priority TEXT NOT NULL, created_at TEXT NOT NULL)")
    count = connection.execute("SELECT COUNT(*) AS total FROM tasks").fetchone()["total"]
    if count == 0:
        connection.execute("INSERT INTO tasks(title,description,status,owner,priority,created_at) VALUES ('Refactor login','Separar responsabilidades en frontend','TODO','student','HIGH',datetime('now'))")
        connection.execute("INSERT INTO tasks(title,description,status,owner,priority,created_at) VALUES ('Review API','Revisar seguridad de endpoints','IN_PROGRESS','student','MEDIUM',datetime('now'))")
        connection.execute("INSERT INTO tasks(title,description,status,owner,priority,created_at) VALUES ('Trainer notes','Preparar retrospectiva','TODO','trainer','LOW',datetime('now'))")
        connection.commit()

    app = FastAPI(title="Workshop Requirements API", version="0.1.0")
    app.state.token_verifier = TokenVerifier.from_environment()
    app.state.connection = connection
    app.state.upload_dir = selected_uploads
    task_service = TaskService(TaskRepository(connection))
    upload_service = UploadService(selected_uploads)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(sqlite3.Error)
    async def task_storage_error(request: Any, error: sqlite3.Error) -> JSONResponse:
        return JSONResponse(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, content={"detail": TASK_STORAGE_ERROR_DETAIL})

    @app.get("/api/tasks")
    def list_tasks(owner: str | None = Query(default=None), identity: Identity = Depends(task_identity)) -> list[Task]:
        return task_service.list_tasks(owner, identity)

    @app.post("/api/tasks", status_code=HTTPStatus.CREATED)
    def create_task(payload: TaskCreate = Body(...), identity: Identity = Depends(task_identity)) -> Task:
        return task_service.create_task(payload, identity)

    @app.get("/api/summary")
    def summary(owner: str | None = Query(default=None), identity: Identity = Depends(task_identity)) -> TaskSummary:
        return task_service.summary(owner, identity)

    @app.post("/api/requirements", status_code=HTTPStatus.CREATED)
    async def upload_requirement(file: UploadFile = File(...), identity: Identity = Depends(task_identity)) -> UploadResult:
        return await upload_service.store(file, identity)

    @app.get("/api/backend-health")
    def backend_health(identity: dict[str, str] = Depends(token_identity)) -> dict[str, Any]:
        url = os.getenv("AUTH_HEALTH_URL", "http://localhost:8080/q/health")
        try:
            response = urllib3.PoolManager().request("GET", url, timeout=3.0)
            return {"requestedBy": identity["username"], "status": response.status, "body": response.data.decode("utf-8")}
        except Exception as error:
            return {"requestedBy": identity["username"], "status": 0, "body": str(error)}

    @app.on_event("shutdown")
    def close_connection() -> None:
        connection.close()

    return app


app = create_app()
