from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import ConfigurationError, Settings
from app.main import create_app
from app.models import UserRole
from tests.conftest import auth_headers_for_client, create_task, legacy_base64_headers


def test_rejects_missing_jwt_secret_in_production(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WORKSHOP_JWT_SECRET", raising=False)
    monkeypatch.setenv("WORKSHOP_ENV", "production")

    with pytest.raises(ConfigurationError):
        Settings.from_env(
            db_path=tmp_path / "workshop.db",
            upload_dir=tmp_path / "uploads",
        )


def test_rejects_legacy_basic_base64_authentication(client: TestClient) -> None:
    response = client.get("/api/tasks", headers=legacy_base64_headers())

    assert response.status_code == 401
    assert response.json()["detail"] == "Unsupported authentication scheme"


def test_rejects_raw_legacy_base64_authentication_without_bearer_scheme(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/tasks",
        headers={"Authorization": legacy_base64_headers()["Authorization"].removeprefix("Basic ")},
    )

    assert response.status_code == 401


def test_rejects_invalid_bearer_token(client: TestClient) -> None:
    response = client.get(
        "/api/tasks",
        headers={"Authorization": "Bearer invalid"},
    )

    assert response.status_code == 401


def test_user_cannot_read_task_owned_by_another_user(client: TestClient) -> None:
    created = create_task(client, username="alice")

    response = client.get(
        f"/api/tasks/{created['id']}",
        headers=auth_headers_for_client(client, username="bob"),
    )

    assert response.status_code == 403


def test_admin_can_read_task_owned_by_another_user(client: TestClient) -> None:
    created = create_task(client, username="alice")

    response = client.get(
        f"/api/tasks/{created['id']}",
        headers=auth_headers_for_client(client, username="admin", role=UserRole.admin),
    )

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_sql_injection_payload_does_not_bypass_task_lookup(client: TestClient) -> None:
    create_task(client, username="alice", title="Alice private")
    bob_task = create_task(client, username="bob", title="Bob private")

    response = client.get(
        f"/api/tasks/{bob_task['id']} OR 1=1",
        headers=auth_headers_for_client(client, username="alice"),
    )

    assert response.status_code == 422


def test_sql_injection_string_is_stored_as_data_not_executed(client: TestClient) -> None:
    malicious_title = "x'); DROP TABLE tasks; --"

    created = create_task(client, username="alice", title=malicious_title)
    listed = client.get(
        "/api/tasks",
        headers=auth_headers_for_client(client, username="alice"),
    )

    assert created["title"] == malicious_title
    assert listed.status_code == 200
    assert any(task["title"] == malicious_title for task in listed.json())


def test_unknown_token_subject_is_rejected(tmp_path: Path) -> None:
    app = create_app(tmp_path / "workshop.db", tmp_path / "uploads")

    with TestClient(app) as client:
        headers = auth_headers_for_client(client, username="mallory")
        response = client.get("/api/tasks", headers=headers)

    assert response.status_code == 401