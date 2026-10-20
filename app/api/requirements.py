from __future__ import annotations

from fastapi import APIRouter

# Deprecated module kept intentionally route-less to avoid duplicate registration.
# Use app.api.routes.requirements instead.
router = APIRouter()