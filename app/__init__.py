from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path


class ConfigurationError(RuntimeError):
    """Raised when application configuration is invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    db_path: Path
    upload_dir: Path
    jwt_secret: str
    environment: str
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    max_upload_bytes: int = 5 * 1024 * 1024
    allowed_upload_extensions: frozenset[str] = frozenset(
        {
            ".csv",
            ".gif",
            ".jpeg",
            ".jpg",
            ".json",
            ".pdf",
            ".png",
            ".txt",
        }
    )

    @classmethod
    def from_env(
        cls,
        *,
        db_path: str | Path | None = None,
        upload_dir: str | Path | None = None,
    ) -> Settings:
        environment = os.getenv("WORKSHOP_ENV", "development").strip().lower()
        raw_secret = os.getenv("WORKSHOP_JWT_SECRET")

        if environment in {"production", "prod"} and not raw_secret:
            raise ConfigurationError(
                "WORKSHOP_JWT_SECRET is required when WORKSHOP_ENV=production"
            )

        jwt_secret = raw_secret or secrets.token_urlsafe(48)

        resolved_db_path = Path(db_path or os.getenv("WORKSHOP_DB_PATH", "workshop.db"))
        resolved_upload_dir = Path(upload_dir or os.getenv("WORKSHOP_UPLOAD_DIR", "uploads"))

        max_upload_bytes = _read_positive_int(
            "WORKSHOP_MAX_UPLOAD_BYTES",
            default=5 * 1024 * 1024,
        )

        token_minutes = _read_positive_int(
            "WORKSHOP_ACCESS_TOKEN_MINUTES",
            default=60,
        )

        return cls(
            db_path=resolved_db_path,
            upload_dir=resolved_upload_dir,
            jwt_secret=jwt_secret,
            environment=environment,
            access_token_minutes=token_minutes,
            max_upload_bytes=max_upload_bytes,
        )


def _read_positive_int(name: str, *, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc

    if value <= 0:
        raise ConfigurationError(f"{name} must be greater than zero")

    return value