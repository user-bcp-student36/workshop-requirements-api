from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import AppSettings
from app.repositories.tasks_repository import TasksRepository
from app.security import Identity, raise_forbidden, raise_unauthorized, validate_jwt
from app.services.requirements_service import RequirementsService
from app.services.tasks_service import TasksService


bearer_scheme = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> AppSettings:
    return request.app.state.settings


def get_current_identity(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Identity:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise_unauthorized()

    settings = get_settings(request)
    return validate_jwt(
        credentials.credentials,
        secret=settings.jwt_secret,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        algorithm=settings.jwt_algorithm,
    )


def require_roles(*roles: str) -> Callable[[Identity], Identity]:
    required_roles = frozenset(role for role in roles if role)

    def dependency(identity: Identity = Depends(get_current_identity)) -> Identity:
        if "admin" in identity.roles:
            return identity

        if required_roles and identity.roles.isdisjoint(required_roles):
            raise_forbidden()

        return identity

    return dependency


def require_permissions(*permissions: str) -> Callable[[Identity], Identity]:
    required_permissions = tuple(permission for permission in permissions if permission)

    def dependency(identity: Identity = Depends(get_current_identity)) -> Identity:
        if "*" in identity.permissions:
            return identity

        if any(not identity.has_permission(permission) for permission in required_permissions):
            raise_forbidden()

        return identity

    return dependency


def get_tasks_service(request: Request) -> TasksService:
    return TasksService(TasksRepository(request.app.state.db))


def get_requirements_service(request: Request) -> RequirementsService:
    settings = get_settings(request)
    return RequirementsService(
        upload_dir=settings.upload_dir,
        max_bytes=settings.upload_max_bytes,
        allowed_extensions=settings.upload_allowed_extensions,
    )