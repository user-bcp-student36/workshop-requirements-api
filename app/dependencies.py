from __future__ import annotations

# Compatibility layer for legacy imports. New code must import from app.api.dependencies.
from app.api.dependencies import (  # noqa: F401
    get_current_identity,
    get_requirements_service,
    get_settings,
    get_tasks_service,
)