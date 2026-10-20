from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from app.models import TokenClaims, UserRole


class AuthenticationError(RuntimeError):
    """Raised when a bearer token cannot be authenticated."""


def create_access_token(
    *,
    username: str,
    role: UserRole | str,
    secret: str,
    expires_in_seconds: int = 3600,
) -> str:
    role_value = role.value if isinstance(role, UserRole) else role
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": username,
        "role": role_value,
        "exp": int(time.time()) + expires_in_seconds,
    }

    encoded_header = _base64url_encode_json(header)
    encoded_payload = _base64url_encode_json(payload)
    signing_input = f"{encoded_header}.{encoded_payload}".encode()
    signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()

    return f"{encoded_header}.{encoded_payload}.{_base64url_encode(signature)}"


def verify_access_token(token: str, *, secret: str) -> TokenClaims:
    parts = token.split(".")
    if len(parts) != 3:
        raise AuthenticationError("Invalid bearer token")

    encoded_header, encoded_payload, encoded_signature = parts
    signing_input = f"{encoded_header}.{encoded_payload}".encode()

    expected_signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    provided_signature = _base64url_decode(encoded_signature)

    if not hmac.compare_digest(expected_signature, provided_signature):
        raise AuthenticationError("Invalid bearer token signature")

    header = _decode_json_part(encoded_header)
    if header.get("alg") != "HS256" or header.get("typ") != "JWT":
        raise AuthenticationError("Unsupported bearer token")

    payload = _decode_json_part(encoded_payload)

    try:
        claims = TokenClaims.model_validate(payload)
    except ValueError as exc:
        raise AuthenticationError("Invalid bearer token claims") from exc

    if claims.exp < int(time.time()):
        raise AuthenticationError("Bearer token expired")

    return claims


def _base64url_encode_json(value: dict[str, Any]) -> str:
    serialized = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
    return _base64url_encode(serialized)


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(f"{value}{padding}")
    except ValueError as exc:
        raise AuthenticationError("Invalid base64url encoding") from exc


def _decode_json_part(value: str) -> dict[str, Any]:
    try:
        decoded = json.loads(_base64url_decode(value))
    except json.JSONDecodeError as exc:
        raise AuthenticationError("Invalid bearer token JSON") from exc

    if not isinstance(decoded, dict):
        raise AuthenticationError("Invalid bearer token JSON object")

    return decoded