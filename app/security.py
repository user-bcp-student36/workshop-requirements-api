from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, NoReturn

import jwt
from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict, SecretStr


class Identity(BaseModel):
    model_config = ConfigDict(frozen=True)

    subject: str
    issuer: str
    audience: str
    roles: frozenset[str]


def _secret_value(secret: str | SecretStr) -> str:
    if isinstance(secret, SecretStr):
        return secret.get_secret_value()
    return secret


def _normalize_roles(raw_roles: Any) -> frozenset[str]:
    if raw_roles is None:
        return frozenset()

    if isinstance(raw_roles, str):
        candidates = raw_roles.split(",")

    elif isinstance(raw_roles, list | tuple | set):
        candidates = raw_roles

    else:
        return frozenset()

    roles = {
        str(role).strip().lower()
        for role in candidates
        if str(role).strip()
    }
    return frozenset(roles)


def raise_unauthorized(detail: str = "Invalid or missing authentication credentials") -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def raise_forbidden(detail: str = "Insufficient permissions") -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
    )


def validate_jwt(
    token: str,
    *,
    secret: str | SecretStr,
    issuer: str,
    audience: str,
    algorithm: str,
) -> Identity:
    """
    Valida un JWT real con issuer, audience, expiración y algoritmo explícito.

    No se aceptan tokens legacy ni tokens sin firma. Los errores se normalizan para
    evitar filtrado de detalles internos de validación.
    """

    if not token or not token.strip():
        raise_unauthorized()

    if algorithm.upper() == "NONE":
        raise_unauthorized()

    try:
        payload = jwt.decode(
            token,
            key=_secret_value(secret),
            algorithms=[algorithm],
            issuer=issuer,
            audience=audience,
            options={
                "require": ["sub", "exp", "iat"],
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_aud": True,
                "verify_iss": True,
            },
        )
    except jwt.PyJWTError:
        raise_unauthorized()

    subject = str(payload.get("sub", "")).strip()
    if not subject:
        raise_unauthorized()

    return Identity(
        subject=subject,
        issuer=issuer,
        audience=audience,
        roles=_normalize_roles(payload.get("roles")),
    )


def create_access_token(
    *,
    subject: str,
    roles: list[str] | tuple[str, ...] | set[str],
    secret: str | SecretStr,
    issuer: str,
    audience: str,
    algorithm: str,
    expires_delta: timedelta = timedelta(minutes=15),
) -> str:
    """
    Helper para emisión controlada de JWT.

    Útil para integraciones internas y fixtures de test. No contiene secretos ni
    credenciales hardcodeadas.
    """

    normalized_subject = subject.strip()
    if not normalized_subject:
        raise ValueError("subject must not be empty")

    now = datetime.now(UTC)
    payload = {
        "sub": normalized_subject,
        "roles": sorted({role.strip().lower() for role in roles if role.strip()}),
        "iss": issuer,
        "aud": audience,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }

    return jwt.encode(
        payload,
        key=_secret_value(secret),
        algorithm=algorithm,
    )