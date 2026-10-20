from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


Environment = Literal["local", "test", "staging", "production"]
JwtAlgorithm = Literal["HS256", "HS384", "HS512"]


class AppSettings(BaseSettings):
    """
    Configuración centralizada de la aplicación.

    Importante:
    - `jwt_secret` no tiene default por seguridad.
    - En ambientes no-test se rechazan secretos débiles o de ejemplo.
    - No se exponen valores secretos en responses ni logs.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Environment = "local"

    database_path: str = Field(default="app.db")
    upload_dir: str = Field(default="uploads")

    jwt_secret: SecretStr
    jwt_issuer: str
    jwt_audience: str
    jwt_algorithm: JwtAlgorithm = "HS256"

    upload_max_bytes: int = Field(default=5 * 1024 * 1024, ge=1, le=25 * 1024 * 1024)
    allowed_upload_extensions: tuple[str, ...] = (".txt", ".md", ".pdf")

    seed_demo_data: bool = False

    @field_validator("jwt_issuer", "jwt_audience")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("JWT issuer/audience must not be empty")
        return normalized

    @field_validator("allowed_upload_extensions")
    @classmethod
    def normalize_upload_extensions(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        for value in values:
            extension = value.strip().lower()
            if not extension:
                continue
            if not extension.startswith("."):
                extension = f".{extension}"
            normalized.append(extension)

        if not normalized:
            raise ValueError("At least one upload extension must be configured")

        return tuple(dict.fromkeys(normalized))

    @model_validator(mode="after")
    def validate_security_settings(self) -> "AppSettings":
        secret = self.jwt_secret.get_secret_value().strip()
        if not secret:
            raise ValueError("JWT secret must not be empty")

        weak_examples = {
            "secret",
            "jwt_secret",
            "changeme",
            "change-me",
            "password",
            "admin",
            "test",
            "example",
            "example-secret",
            "dev-secret",
        }

        if self.environment != "test":
            if len(secret) < 32:
                raise ValueError("JWT secret must contain at least 32 characters outside test")
            if secret.lower() in weak_examples:
                raise ValueError("JWT secret must not use weak/example values outside test")
            if len(set(secret)) < 8:
                raise ValueError("JWT secret must have sufficient entropy outside test")

        return self

    @property
    def database_file(self) -> Path:
        return Path(self.database_path)

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir)