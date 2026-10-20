from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile, status

from app.config import Settings
from app.models import TaskCreate, TaskUpdate, UserPrincipal
from app.repositories import TaskRepository, UploadRepository


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    def list_tasks(self, principal: UserPrincipal) -> list[dict[str, Any]]:
        return self._repository.list_for_user(principal)

    def create_task(self, payload: TaskCreate, principal: UserPrincipal) -> dict[str, Any]:
        return self._repository.create(payload, principal)

    def get_task(self, task_id: int, principal: UserPrincipal) -> dict[str, Any]:
        task = self._get_existing_task(task_id)
        self._authorize_resource_owner(task, principal)
        return task

    def update_task(
        self,
        task_id: int,
        payload: TaskUpdate,
        principal: UserPrincipal,
    ) -> dict[str, Any]:
        task = self._get_existing_task(task_id)
        self._authorize_resource_owner(task, principal)

        updated = self._repository.update(task_id, payload)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

        return updated

    def delete_task(self, task_id: int, principal: UserPrincipal) -> None:
        task = self._get_existing_task(task_id)
        self._authorize_resource_owner(task, principal)
        self._repository.delete(task_id)

    def _get_existing_task(self, task_id: int) -> dict[str, Any]:
        task = self._repository.get_by_id(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return task

    @staticmethod
    def _authorize_resource_owner(task: dict[str, Any], principal: UserPrincipal) -> None:
        if principal.is_admin:
            return

        if int(task["owner_id"]) != principal.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


class UploadService:
    def __init__(
        self,
        *,
        settings: Settings,
        task_repository: TaskRepository,
        upload_repository: UploadRepository,
    ) -> None:
        self._settings = settings
        self._task_repository = task_repository
        self._upload_repository = upload_repository

    async def create_upload(
        self,
        *,
        task_id: int,
        file: UploadFile,
        principal: UserPrincipal,
    ) -> dict[str, Any]:
        task = self._task_repository.get_by_id(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

        TaskService._authorize_resource_owner(task, principal)

        original_filename = _validate_original_filename(file.filename)
        extension = Path(original_filename).suffix.lower()

        if extension not in self._settings.allowed_upload_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File extension is not allowed",
            )

        content = await file.read(self._settings.max_upload_bytes + 1)
        if len(content) > self._settings.max_upload_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File is too large",
            )

        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File cannot be empty",
            )

        _validate_file_content(extension=extension, content=content)

        stored_filename = f"{uuid.uuid4().hex}{extension}"
        destination = _safe_destination(self._settings.upload_dir, stored_filename)

        self._settings.upload_dir.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)

        return self._upload_repository.create(
            task_id=task_id,
            owner_id=int(task["owner_id"]),
            original_filename=original_filename,
            stored_filename=stored_filename,
            content_type=file.content_type or "application/octet-stream",
            size_bytes=len(content),
        )

    def get_upload(self, upload_id: int, principal: UserPrincipal) -> dict[str, Any]:
        upload = self._upload_repository.get_by_id(upload_id)
        if upload is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")

        if not principal.is_admin and int(upload["owner_id"]) != principal.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        return upload


def _validate_original_filename(filename: str | None) -> str:
    if filename is None or not filename.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    stripped = filename.strip()

    if "/" in stripped or "\\" in stripped:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path traversal is not allowed",
        )

    normalized = Path(stripped).name
    if normalized != stripped or normalized in {"", ".", ".."}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )

    return normalized


def _safe_destination(upload_dir: Path, stored_filename: str) -> Path:
    resolved_dir = upload_dir.resolve()
    destination = (resolved_dir / stored_filename).resolve()

    if os.path.commonpath([str(resolved_dir), str(destination)]) != str(resolved_dir):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid upload destination",
        )

    return destination


def _validate_file_content(*, extension: str, content: bytes) -> None:
    validators = {
        ".csv": _validate_text_content,
        ".gif": _validate_gif_content,
        ".jpeg": _validate_jpeg_content,
        ".jpg": _validate_jpeg_content,
        ".json": _validate_json_content,
        ".pdf": _validate_pdf_content,
        ".png": _validate_png_content,
        ".txt": _validate_text_content,
    }

    validator = validators.get(extension)
    if validator is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File extension is not allowed",
        )

    validator(content)


def _validate_text_content(content: bytes) -> None:
    if b"\x00" in content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid text file content",
        )

    try:
        content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text files must be UTF-8 encoded",
        ) from exc


def _validate_json_content(content: bytes) -> None:
    _validate_text_content(content)

    try:
        json.loads(content.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON file content",
        ) from exc


def _validate_pdf_content(content: bytes) -> None:
    if not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid PDF file content",
        )


def _validate_png_content(content: bytes) -> None:
    if not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid PNG file content",
        )


def _validate_jpeg_content(content: bytes) -> None:
    if not (content.startswith(b"\xff\xd8") and content.endswith(b"\xff\xd9")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JPEG file content",
        )


def _validate_gif_content(content: bytes) -> None:
    if not (content.startswith(b"GIF87a") or content.startswith(b"GIF89a")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid GIF file content",
        )