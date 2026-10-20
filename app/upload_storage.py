from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import BinaryIO

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

UPLOAD_MAX_BYTES = 5 * 1024 * 1024
UPLOAD_CHUNK_BYTES = 64 * 1024
TEMPORARY_UPLOAD_PREFIX = ".upload-"


class UploadTooLargeError(ValueError):
    pass


async def write_limited_content(upload: UploadFile, destination: BinaryIO) -> int:
    size = 0
    while content := await upload.read(UPLOAD_CHUNK_BYTES):
        size += len(content)
        if size > UPLOAD_MAX_BYTES:
            raise UploadTooLargeError
        await run_in_threadpool(destination.write, content)
    return size


async def store_upload(upload: UploadFile, target: Path) -> int:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=target.parent, prefix=TEMPORARY_UPLOAD_PREFIX, delete=False) as destination:
            temporary_path = Path(destination.name)
            size = await write_limited_content(upload, destination)
        await run_in_threadpool(os.link, temporary_path, target)
        return size
    finally:
        if temporary_path is not None:
            await run_in_threadpool(temporary_path.unlink, missing_ok=True)