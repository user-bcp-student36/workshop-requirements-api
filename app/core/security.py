from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import timedelta
from typing import Any

from app.core.config import Settings


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _json_dumps(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _sign(message: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
    return _base64url_encode(digest)


def create_access_token(
    *,
    subject: str,
    role: str,
    settings: Settings,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = int(time.time())
    expires_in = expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)

    header = {
        "alg": settings.jwt_algorithm,
        "typ": "JWT",
    }
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + int(expires_in.total_seconds()),
    }

    if extra_claims:
        payload.update(extra_claims)

    encoded_header = _base64url_encode(_json_dumps(header))
    encoded_payload = _base64url_encode(_json_dumps(payload))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = _sign(signing_input, settings.jwt_secret_key)

    return f"{encoded_header}.{encoded_payload}.{signature}"


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
    except ValueError as error:
        raise ValueError("Malformed token") from error

    try:
        header = json.loads(_base64url_decode(encoded_header))
        payload = json.loads(_base64url_decode(encoded_payload))
    except Exception as error:
        raise ValueError("Invalid token encoding") from error

    if header.get("alg") != settings.jwt_algorithm or header.get("typ") != "JWT":
        raise ValueError("Unsupported token header")

    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    expected_signature = _sign(signing_input, settings.jwt_secret_key)

    if not hmac.compare_digest(expected_signature, encoded_signature):
        raise ValueError("Invalid token signature")

    exp = payload.get("exp")
    if not isinstance(exp, int) or exp < int(time.time()):
        raise ValueError("Expired token")

    if not payload.get("sub") or not payload.get("role"):
        raise ValueError("Missing required claims")

    return payload