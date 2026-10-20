from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path


def _csv_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw_value = os.getenv(name)
    if not raw_value:
        return default

    values = tuple(value.strip() for value in raw_value.split(",") if value.strip())
    return values or default


@dataclass(frozen=True)
class Settings:
    db_path: str
    upload_dir: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    cors_allow_origins: tuple[str, ...] = ("*",)

    requirements_max_bytes: int = 1_048_576
    requirements_allowed_extensions: tuple[str, ...] = (".txt", ".md")
    requirements_allowed_content_types: tuple[str, ...] = (
        "text/plain",
        "text/markdown",
        "application/octet-stream",
    )

    @classmethod
    def from_env(
        cls,
        db_path: str | None = None,
        upload_dir: str | None = None,
        jwt_secret_key: str | None = None,
    ) -> "Settings":
        selected_db_path = db_path or os.getenv("WORKSHOP_DB_PATH", "./data/workshop.db")
        selected_upload_dir = upload_dir or os.getenv("WORKSHOP_UPLOAD_DIR", "./uploads")

        # No hay secreto hardcodeado. En producción debe configurarse por entorno.
        # Si no existe, se genera uno efímero para evitar arrancar con un valor
        # inseguro conocido/reutilizable.
        selected_jwt_secret = (
            jwt_secret_key
            or os.getenv("WORKSHOP_JWT_SECRET_KEY")
            or os.getenv("JWT_SECRET_KEY")
            or secrets.token_urlsafe(32)
        )

        expire_minutes_raw = os.getenv("WORKSHOP_JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
        max_bytes_raw = os.getenv("WORKSHOP_REQUIREMENTS_MAX_BYTES", "1048576")

        Path(selected_db_path).parent.mkdir(parents=True, exist_ok=True)
        Path(selected_upload_dir).mkdir(parents=True, exist_ok=True)

        return cls(
            db_path=selected_db_path,
            upload_dir=selected_upload_dir,
            jwt_secret_key=selected_jwt_secret,
            jwt_access_token_expire_minutes=int(expire_minutes_raw),
            cors_allow_origins=_csv_env("WORKSHOP_CORS_ALLOW_ORIGINS", ("*",)),
            requirements_max_bytes=int(max_bytes_raw),
            requirements_allowed_extensions=_csv_env(
                "WORKSHOP_REQUIREMENTS_ALLOWED_EXTENSIONS",
                (".txt", ".md"),
            ),
            requirements_allowed_content_types=_csv_env(
                "WORKSHOP_REQUIREMENTS_ALLOWED_CONTENT_TYPES",
                ("text/plain", "text/markdown", "application/octet-stream"),
            ),
        )