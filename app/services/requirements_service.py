from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.schemas import RequirementUploadRead


_SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


class RequirementsService:
    def __init__(
        self,
        *,
        upload_dir: str | Path,
        max_bytes: int,
        allowed_extensions: tuple[str, ...],
    ) -> None:
        self.upload_dir = Path(upload_dir)
        self.max_bytes = max_bytes
        self.allowed_extensions = tuple(extension.lower() for extension in allowed_extensions)

    async def save_upload(self, file: UploadFile) -> RequirementUploadRead:
        original_filename = file.filename or ""
        safe_filename = self._sanitize_filename(original_filename)
        extension = Path(safe_filename).suffix.lower()

        if extension not in self.allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file extension.",
            )

        self.upload_dir.mkdir(parents=True, exist_ok=True)

        stored_filename = self._build_stored_filename(safe_filename)
        destination = (self.upload_dir / stored_filename).resolve()
        upload_root = self.upload_dir.resolve()

        # Defensa adicional ante traversal si cambia la sanitización en el futuro.
        if upload_root not in destination.parents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid upload destination.",
            )

        total_bytes = 0
        temp_path: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=self.upload_dir,
                prefix=".upload-",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)

                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break

                    total_bytes += len(chunk)
                    if total_bytes > self.max_bytes:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail="Uploaded file is too large.",
                        )

                    temp_file.write(chunk)

            os.replace(temp_path, destination)
            os.chmod(destination, 0o600)

            return RequirementUploadRead(
                original_filename=original_filename,
                stored_filename=stored_filename,
                size_bytes=total_bytes,
            )
        finally:
            await file.close()
            if temp_path is not None and temp_path.exists():
                temp_path.unlink(missing_ok=True)

    def _sanitize_filename(self, filename: str) -> str:
        basename = Path(filename).name.strip()
        if not basename or basename in {".", ".."}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filename.",
            )

        sanitized = _SAFE_FILENAME_PATTERN.sub("_", basename)
        if sanitized.startswith("."):
            sanitized = sanitized.lstrip(".")

        if not sanitized:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filename.",
            )

        return sanitized

    def _build_stored_filename(self, safe_filename: str) -> str:
        path = Path(safe_filename)
        stem = path.stem[:80] or "upload"
        extension = path.suffix.lower()
        return f"{stem}-{uuid4().hex}{extension}"