from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models import UserRole
from app.security import create_access_token


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    app = create_app(
        db_path=tmp_path / "workshop.db",
        upload_dir=tmp_path / "uploads",
    )
    with TestClient(app) as test_client:
        yield test_client


def auth_headers_for_client(
    client: TestClient,
    *,
    username: str = "alice",
    role: UserRole | str = UserRole.user,
) -> dict[str, str]:
    token = create_access_token(
        username=username,
        role=role,
        secret=client.app.state.settings.jwt_secret,
    )
    return {"Authorization": f"Bearer {token}"}


def legacy_base64_headers(*, username: str = "alice", password: str = "password") -> dict[str, str]:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def create_task(
    client: TestClient,
    *,
    username: str = "alice",
    role: UserRole | str = UserRole.user,
    title: str = "Private task",
) -> dict[str, Any]:
    response = client.post(
        "/api/tasks",
        headers=auth_headers_for_client(client, username=username, role=role),
        json={
            "title": title,
            "description": "Task description",
            "status": "TODO",
            "priority": "HIGH",
        },
    )
    assert response.status_code == 201
    return response.json()