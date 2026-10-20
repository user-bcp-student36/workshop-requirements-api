from __future__ import annotations

import ntpath
import unicodedata
from http import HTTPStatus
from pathlib import Path, PurePosixPath, PureWindowsPath

from fastapi import HTTPException, UploadFile

from app.models import Identity, UploadResult
from app.upload_storage import UploadTooLargeError, store_upload

UPLOAD_ALLOWED_EXTENSIONS = frozenset({".txt", ".md", ".pdf"})
INVALID_NAME_DETAIL = "Invalid file name"
INVALID_EXTENSION_DETAIL = "File extension not allowed"
UPLOAD_LIMIT_DETAIL = "File exceeds upload limit"
UPLOAD_COLLISION_DETAIL = "File already exists"
UPLOAD_STORAGE_ERROR_DETAIL = "Upload storage error"


def normalize_file_name(name: str | None) -> str:
    if not name:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=INVALID_NAME_DETAIL)
    normalized = unicodedata.normalize("NFC", name)
    windows_name = PureWindowsPath(normalized)
    if (
        normalized in {".", ".."}
        or PurePosixPath(normalized).name != normalized
        or windows_name.name != normalized
        or windows_name.drive
        or ntpath.isreserved(normalized)
    ):
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=INVALID_NAME_DETAIL)
    return normalized


def upload_destination(directory: Path, name: str | None) -> Path:
    normalized = normalize_file_name(name)
    target = directory / normalized
    if not target.resolve().is_relative_to(directory.resolve()):
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=INVALID_NAME_DETAIL)
    if target.suffix.casefold() not in UPLOAD_ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE, detail=INVALID_EXTENSION_DETAIL)
    return target


class UploadService:
    def __init__(self, directory: str) -> None:
        self.directory = Path(directory)

    async def store(self, file: UploadFile, identity: Identity) -> UploadResult:
        try:
            target = upload_destination(self.directory, file.filename)
            size = await store_upload(file, target)
        except UploadTooLargeError as error:
            raise HTTPException(status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE, detail=UPLOAD_LIMIT_DETAIL) from error
        except FileExistsError as error:
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=UPLOAD_COLLISION_DETAIL) from error
        except OSError as error:
            raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=UPLOAD_STORAGE_ERROR_DETAIL) from error
        return UploadResult(owner=identity.username, file_name=file.filename, stored_at=str(target), size=size)