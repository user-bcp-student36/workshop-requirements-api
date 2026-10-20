from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.schemas.requirements import RequirementUploadResponse


_SAFE_FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9._ -]+$")


class RequirementsService:
    def __init__(
        self,
        *,
        upload_dir: str | Path,
        allowed_extensions: tuple[str, ...],
        max_bytes: int,
    ) -> None:
        self.upload_dir = Path(upload_dir)
        self.allowed_extensions = tuple(extension.lower() for extension in allowed_extensions)
        self.max_bytes = max_bytes
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def validate_upload_metadata(self, file: UploadFile) -> str:
        filename = (file.filename or "").strip()
        if not filename:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Filename is required",
            )

        # Rechaza path traversal en vez de normalizar silenciosamente.
        if Path(filename).name != filename or "/" in filename or "\\" in filename:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Filename must not contain path separators",
            )

        if not _SAFE_FILENAME_PATTERN.fullmatch(filename):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Filename contains unsupported characters",
            )

        extension = Path(filename).suffix.lower()
        if extension not in self.allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Unsupported file extension",
            )

        return filename

    def save_upload(self, *, file: UploadFile, content: bytes) -> RequirementUploadResponse:
        original_filename = self.validate_upload_metadata(file)

        if len(content) > self.max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File exceeds configured maximum size",
            )

        upload_id = uuid.uuid4().hex
        stored_filename = f"{upload_id}{Path(original_filename).suffix.lower()}"
        destination = self._safe_destination(stored_filename)

        destination.write_bytes(content)

        return RequirementUploadResponse(
            id=upload_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            content_type=file.content_type or "application/octet-stream",
            size_bytes=len(content),
            created_at=datetime.now(UTC),
        )

    def _safe_destination(self, stored_filename: str) -> Path:
        upload_root = self.upload_dir.resolve()
        destination = (upload_root / stored_filename).resolve()

        # Defensa explícita contra escritura fuera del directorio configurado.
        if destination.parent != upload_root:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid upload destination",
            )

        return destination