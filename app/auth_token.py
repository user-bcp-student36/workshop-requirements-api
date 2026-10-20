from __future__ import annotations

import os
import time
from collections.abc import Callable
from pathlib import Path

import jwt
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey


class InvalidTokenError(ValueError):
    pass


class TokenVerifier:
    def __init__(
        self, public_key: RSAPublicKey | None, issuer: str, audience: str,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.public_key = public_key
        self.issuer = issuer
        self.audience = audience
        self.clock = clock

    @classmethod
    def from_environment(cls) -> TokenVerifier:
        key_path = os.getenv("AUTH_TOKEN_PUBLIC_KEY_LOCATION", "")
        issuer = os.getenv("AUTH_TOKEN_ISSUER", "")
        audience = os.getenv("AUTH_TOKEN_AUDIENCE", "")
        try:
            loaded_key = serialization.load_pem_public_key(Path(key_path).read_bytes())
        except (OSError, ValueError, UnsupportedAlgorithm):
            return cls(None, issuer, audience)
        if not isinstance(loaded_key, RSAPublicKey) or loaded_key.key_size < 2048:
            return cls(None, issuer, audience)
        return cls(loaded_key, issuer, audience)

    def verify(self, authorization: str) -> dict[str, str]:
        scheme, separator, token = authorization.partition(" ")
        if (
            self.public_key is None or not self.issuer.strip() or not self.audience.strip()
            or scheme.lower() != "bearer" or not separator or not token or any(character.isspace() for character in token)
        ):
            raise InvalidTokenError()
        try:
            claims = jwt.decode(
                token, self.public_key, algorithms=["RS256"], issuer=self.issuer, audience=self.audience,
                options={"require": ["sub", "groups", "iss", "aud", "exp"], "verify_exp": False, "verify_iat": False},
            )
        except jwt.InvalidTokenError as error:
            raise InvalidTokenError() from error
        expiration = claims["exp"]
        username = claims["sub"]
        groups = claims["groups"]
        now = self.clock() if self.clock is not None else time.time()
        if (
            type(expiration) is not int or now >= expiration
            or not isinstance(username, str) or not username
            or not isinstance(groups, list) or len(groups) != 1
            or not isinstance(groups[0], str) or not groups[0]
        ):
            raise InvalidTokenError()
        return {"username": username, "role": groups[0]}