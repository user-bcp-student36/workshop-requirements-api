from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


_INSECURE_SECRET_VALUES = {
    "",
    "secret",
    "changeme",
    "change-me",
    "WORKSHOP_SECRET_2026",
    "workshop",
    "dev-secret",
}


@dataclass(frozen=True)
class AppSettings:
    database_path: Path
    upload_dir: Path

    jwt_secret: str
    jwt_issuer: str
    jwt_audience: str
    jwt_algorithm: str = "HS256"

    upload_max_bytes: int = 5 * 1024 * 1024
    upload_allowed_extensions: tuple[str, ...] = (".txt", ".md", ".pdf")

    seed_demo_data: bool = False

    @classmethod
    def from_env(
        cls,
        *,
        database_path: str | Path | None = None,
        upload_dir: str | Path | None = None,
        jwt_secret: str | None = None,
        jwt_issuer: str | None = None,
        jwt_audience: str | None = None,
        seed_demo_data: bool | None = None,
    ) -> "AppSettings":
        settings = cls(
            database_path=Path(
                database_path
                or os.getenv("WORKSHOP_DATABASE_PATH")
                or os.getenv("DATABASE_PATH")
                or "workshop.db"
            ),
            upload_dir=Path(
                upload_dir
                or os.getenv("WORKSHOP_UPLOAD_DIR")
                or os.getenv("UPLOAD_DIR")
                or "uploads"
            ),
            jwt_secret=jwt_secret
            or os.getenv("WORKSHOP_JWT_SECRET")
            or os.getenv("JWT_SECRET")
            or "",
            jwt_issuer=jwt_issuer
            or os.getenv("WORKSHOP_JWT_ISSUER")
            or os.getenv("JWT_ISSUER")
            or "workshop-api",
            jwt_audience=jwt_audience
            or os.getenv("WORKSHOP_JWT_AUDIENCE")
            or os.getenv("JWT_AUDIENCE")
            or "workshop-clients",
            jwt_algorithm=os.getenv("WORKSHOP_JWT_ALGORITHM", "HS256"),
            upload_max_bytes=int(os.getenv("WORKSHOP_UPLOAD_MAX_BYTES", str(5 * 1024 * 1024))),
            upload_allowed_extensions=_parse_extensions(
                os.getenv("WORKSHOP_UPLOAD_ALLOWED_EXTENSIONS", ".txt,.md,.pdf")
            ),
            seed_demo_data=_parse_bool(
                os.getenv("WORKSHOP_SEED_DEMO_DATA"),
                default=False if seed_demo_data is None else seed_demo_data,
            ),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.jwt_algorithm not in {"HS256", "HS384", "HS512"}:
            raise RuntimeError("Unsupported JWT algorithm. Use HS256, HS384 or HS512.")

        normalized_secret = self.jwt_secret.strip()
        if normalized_secret in _INSECURE_SECRET_VALUES:
            raise RuntimeError("JWT secret must be explicitly configured and cannot use insecure defaults.")

        # Para HMAC JWT en producción se exige entropía mínima razonable.
        if len(normalized_secret.encode("utf-8")) < 32:
            raise RuntimeError("JWT secret must be at least 32 bytes long.")

        if not self.jwt_issuer.strip():
            raise RuntimeError("JWT issuer must be configured.")

        if not self.jwt_audience.strip():
            raise RuntimeError("JWT audience must be configured.")

        if self.upload_max_bytes <= 0:
            raise RuntimeError("Upload max bytes must be greater than zero.")

        if not self.upload_allowed_extensions:
            raise RuntimeError("At least one upload extension must be configured.")

        for extension in self.upload_allowed_extensions:
            if not extension.startswith(".") or "/" in extension or "\\" in extension:
                raise RuntimeError(f"Invalid upload extension configured: {extension}")


def _parse_extensions(raw: str) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                value.strip().lower()
                for value in raw.split(",")
                if value.strip()
            }
        )
    )


def _parse_bool(raw: str | None, *, default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}