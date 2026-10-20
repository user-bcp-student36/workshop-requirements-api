from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.config import Settings
from app.dependencies import get_current_principal, get_db, get_settings
from app.models import UploadResponse, UserPrincipal
from app.repositories import TaskRepository, UploadRepository
from app.services import UploadService

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    task_id: Annotated[int, Form(gt=0)],
    file: Annotated[UploadFile, File()],
    principal: Annotated[UserPrincipal, Depends(get_current_principal)],
    settings: Annotated[Settings, Depends(get_settings)],
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
) -> dict[str, object]:
    service = UploadService(
        settings=settings,
        task_repository=TaskRepository(connection),
        upload_repository=UploadRepository(connection),
    )
    return await service.create_upload(task_id=task_id, file=file, principal=principal)


@router.get("/{upload_id}", response_model=UploadResponse)
def get_upload(
    upload_id: int,
    principal: Annotated[UserPrincipal, Depends(get_current_principal)],
    settings: Annotated[Settings, Depends(get_settings)],
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
) -> dict[str, object]:
    service = UploadService(
        settings=settings,
        task_repository=TaskRepository(connection),
        upload_repository=UploadRepository(connection),
    )
    return service.get_upload(upload_id, principal)