from __future__ import annotations

from fastapi import HTTPException, status

from app.schemas.auth import CurrentUser


class AuthorizationService:
    ADMIN_ROLE = "admin"

    def is_admin(self, user: CurrentUser) -> bool:
        return user.role.lower() == self.ADMIN_ROLE

    def resolve_owner_scope(self, *, current_user: CurrentUser, requested_owner: str | None = None) -> str | None:
        if self.is_admin(current_user):
            return requested_owner

        if requested_owner is not None and requested_owner != current_user.username:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access resources for this owner",
            )

        return current_user.username

    def ensure_owner_access(self, *, current_user: CurrentUser, resource_owner: str) -> None:
        if self.is_admin(current_user):
            return

        if resource_owner != current_user.username:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this resource",
            )