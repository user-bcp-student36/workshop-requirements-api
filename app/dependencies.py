from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from app.config import Settings
from app.db import connect
from app.models import UserPrincipal
from app.repositories import UserRepository
from app.security import AuthenticationError, verify_access_token


def get_settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        raise RuntimeError("Application settings were not initialized")
    return settings


def get_db(settings: Annotated[Settings, Depends(get_settings)]) -> Iterator[sqlite3.Connection]:
    connection = connect(settings.db_path)
    try:
        yield connection
    finally:
        connection.close()


def get_current_principal(
    authorization: Annotated[str | None, Header()] = None,
    settings: Annotated[Settings, Depends(get_settings)] = Depends(),
    connection: Annotated[sqlite3.Connection, Depends(get_db)] = Depends(),
) -> UserPrincipal:
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unsupported authentication scheme",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = verify_access_token(token.strip(), secret=settings.jwt_secret)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = UserRepository(connection).get_by_username(claims.sub)
    if user is None or user.role != claims.role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unknown token subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user