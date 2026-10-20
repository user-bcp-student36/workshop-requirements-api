from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any, Mapping

from fastapi import HTTPException, status


@dataclass(frozen=True)
class Identity:
    sub: str
    roles: frozenset[str]
    permissions: frozenset[str]
    issuer: str
    audience: str
    expires_at: int
    claims: Mapping[str, Any]

    @property
    def username(self) -> str:
        # Compatibilidad semántica con código anterior que usaba username.
        return self.sub

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def has_permission(self, permission: str) -> bool:
        return "*" in self.permissions or permission in self.permissions


_ROLE_DEFAULT_PERMISSIONS: dict[str, frozenset[str]] = {
    "admin": frozenset({"*"}),
    "lead": frozenset(
        {
            "tasks:read",
            "tasks:create",
            "tasks:update",
            "tasks:delete",
            "summary:read",
            "requirements:upload",
        }
    ),
    "student": frozenset(
        {
            "tasks:read",
            "tasks:create",
            "summary:read",
            "requirements:upload",
        }
    ),
}


_HASH_BY_ALGORITHM = {
    "HS256": hashlib.sha256,
    "HS384": hashlib.sha384,
    "HS512": hashlib.sha512,
}


def authenticate_bearer_token(
    authorization: str,
    *,
    secret: str,
    issuer: str,
    audience: str,
    algorithm: str = "HS256",
) -> Identity:
    if not authorization:
        raise_unauthorized()

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise_unauthorized()

    return validate_jwt(
        token,
        secret=secret,
        issuer=issuer,
        audience=audience,
        algorithm=algorithm,
    )


def validate_jwt(
    token: str,
    *,
    secret: str,
    issuer: str,
    audience: str,
    algorithm: str = "HS256",
) -> Identity:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".", 2)
    except ValueError:
        raise_unauthorized()

    header = _decode_json_segment(header_b64)
    claims = _decode_json_segment(payload_b64)

    token_algorithm = header.get("alg")
    if token_algorithm != algorithm:
        raise_unauthorized()

    if token_algorithm not in _HASH_BY_ALGORITHM:
        raise_unauthorized()

    if header.get("typ") not in {None, "JWT"}:
        raise_unauthorized()

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        signing_input,
        _HASH_BY_ALGORITHM[token_algorithm],
    ).digest()

    received_signature = _base64url_decode(signature_b64)
    if not hmac.compare_digest(expected_signature, received_signature):
        raise_unauthorized()

    now = int(time.time())

    exp = _required_int_claim(claims, "exp")
    if exp <= now:
        raise_unauthorized()

    nbf = _optional_int_claim(claims, "nbf")
    if nbf is not None and nbf > now:
        raise_unauthorized()

    iat = _optional_int_claim(claims, "iat")
    if iat is not None and iat > now:
        raise_unauthorized()

    if claims.get("iss") != issuer:
        raise_unauthorized()

    if not _audience_matches(claims.get("aud"), audience):
        raise_unauthorized()

    sub = claims.get("sub")
    if not isinstance(sub, str) or not sub.strip():
        raise_unauthorized()

    roles = _extract_string_set(claims.get("roles"))
    legacy_role = claims.get("role")
    if isinstance(legacy_role, str) and legacy_role.strip():
        roles.add(legacy_role.strip())

    permissions = _extract_string_set(claims.get("permissions"))
    permissions.update(_extract_string_set(claims.get("perms")))

    scope = claims.get("scope")
    if isinstance(scope, str):
        permissions.update(value for value in scope.split() if value)

    # Permite tokens compactos con roles solamente, sin duplicar todos los permisos.
    for role in roles:
        permissions.update(_ROLE_DEFAULT_PERMISSIONS.get(role, frozenset()))

    return Identity(
        sub=sub.strip(),
        roles=frozenset(roles),
        permissions=frozenset(permissions),
        issuer=issuer,
        audience=audience,
        expires_at=exp,
        claims=claims,
    )


def raise_unauthorized() -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication token.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def raise_forbidden() -> None:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions.",
    )


def _decode_json_segment(segment: str) -> dict[str, Any]:
    try:
        decoded = _base64url_decode(segment)
        value = json.loads(decoded.decode("utf-8"))
    except Exception:
        raise_unauthorized()

    if not isinstance(value, dict):
        raise_unauthorized()

    return value


def _base64url_decode(value: str) -> bytes:
    try:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode((value + padding).encode("ascii"))
    except Exception:
        raise_unauthorized()


def _required_int_claim(claims: Mapping[str, Any], name: str) -> int:
    value = claims.get(name)
    if not isinstance(value, int):
        raise_unauthorized()
    return value


def _optional_int_claim(claims: Mapping[str, Any], name: str) -> int | None:
    value = claims.get(name)
    if value is None:
        return None
    if not isinstance(value, int):
        raise_unauthorized()
    return value


def _audience_matches(claim_audience: Any, expected_audience: str) -> bool:
    if isinstance(claim_audience, str):
        return claim_audience == expected_audience

    if isinstance(claim_audience, list):
        return expected_audience in claim_audience

    return False


def _extract_string_set(raw: Any) -> set[str]:
    if raw is None:
        return set()

    if isinstance(raw, str):
        value = raw.strip()
        return {value} if value else set()

    if isinstance(raw, list):
        return {value.strip() for value in raw if isinstance(value, str) and value.strip()}

    return set()