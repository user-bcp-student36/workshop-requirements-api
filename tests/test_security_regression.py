from __future__ import annotations

import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import ConfigurationError, Settings
from app.main import create_app


def auth_headers(app, username: str = "student", role: str = "student") -> dict[str, str]:
    token = app.state.jwt_service.create_access_token(username=username, role=role)
    return {"Authorization": f"Bearer {token}"}


def legacy_base64_headers() -> dict[str, str]:
    token = base64.b64encode(b"student:password").decode("ascii")
    return {"Authorization": f"Basic {token}"}


def test_rejects_weak_configured_jwt_secret(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKSHOP_JWT_SECRET", "changeme")
    monkeypatch.setenv("WORKSHOP_ENV", "production")

    with pytest.raises(ConfigurationError):
        Settings.from_env(
            db_path=str(tmp_path / "workshop.db"),
            upload_dir=str(tmp_path / "uploads"),
        )


def test_rejects_missing_jwt_secret_in_production(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WORKSHOP_JWT_SECRET", raising=False)
    monkeypatch.setenv("WORKSHOP_ENV", "production")

    with pytest.raises(ConfigurationError):
        Settings.from_env(
            db_path=str(tmp_path / "workshop.db"),
            upload_dir=str(tmp_path / "uploads"),
        )


def test_rejects_legacy_base64_authentication(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=legacy_base64_headers())

    assert response.status_code == 401


def test_rejects_invalid_bearer_token(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    with TestClient(app) as client:
        response = client.get(
            "/api/tasks",
            headers={"Authorization": "Bearer invalid"},
        )

    assert response.status_code == 401


def test_user_cannot_read_task_owned_by_another_user(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    with TestClient(app) as client:
        created = client.post(
            "/api/tasks",
            headers=auth_headers(app, username="alice"),
            json={
                "title": "Private task",
                "description": "Only Alice can read this.",
                "status": "TODO",
                "priority": "HIGH",
            },
        )
        response = client.get(
            f"/api/tasks/{created.json()['id']}",
            headers=auth_headers(app, username="bob"),
        )

    assert created.status_code == 201
    assert response.status_code == 403


def test_admin_can_read_task_owned_by_another_user(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    with TestClient(app) as client:
        created = client.post(
            "/api/tasks",
            headers=auth_headers(app, username="alice"),
            json={
                "title": "Private task",
                "description": "Admin can read this.",
                "status": "TODO",
                "priority": "HIGH",
            },
        )
        response = client.get(
            f"/api/tasks/{created.json()['id']}",
            headers=auth_headers(app, username="admin", role="admin"),
        )

    assert created.status_code == 201
    assert response.status_code == 200
    assert response.json()["owner"] == "alice"


def test_rejects_unexpected_task_payload_fields(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    with TestClient(app) as client:
        response = client.post(
            "/api/tasks",
            headers=auth_headers(app),
            json={
                "title": "Unexpected",
                "description": "Extra field should be rejected.",
                "status": "TODO",
                "priority": "LOW",
                "owner": "attacker",
            },
        )

    assert response.status_code == 422


def test_upload_uses_random_stored_filename_and_owner(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    with TestClient(app) as client:
        response = client.post(
            "/api/uploads",
            headers=auth_headers(app, username="alice"),
            files={"file": ("evidence.txt", b"safe content", "text/plain")},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["original_filename"] == "evidence.txt"
    assert body["stored_filename"] != "evidence.txt"
    assert body["stored_filename"].endswith(".txt")
    assert body["owner"] == "alice"
    assert (tmp_path / "uploads" / body["stored_filename"]).exists()


def test_upload_rejects_path_traversal(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    with TestClient(app) as client:
        response = client.post(
            "/api/uploads",
            headers=auth_headers(app),
            files={"file": ("../evil.txt", b"evil", "text/plain")},
        )

    assert response.status_code == 400


def test_upload_rejects_dangerous_extension(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    with TestClient(app) as client:
        response = client.post(
            "/api/uploads",
            headers=auth_headers(app),
            files={"file": ("shell.sh", b"#!/bin/sh", "text/x-shellscript")},
        )

    assert response.status_code == 400


def test_upload_rejects_excessive_size(tmp_path: Path) -> None:
    settings = Settings(
        db_path=str(tmp_path / "workshop.db"),
        upload_dir=str(tmp_path / "uploads"),
        jwt_secret="x" * 48,
        max_upload_size_bytes=4,
    )
    app = create_app(settings=settings)

    with TestClient(app) as client:
        response = client.post(
            "/api/uploads",
            headers=auth_headers(app),
            files={"file": ("large.txt", b"too large", "text/plain")},
        )

    assert response.status_code == 413
    assert list((tmp_path / "uploads").iterdir()) == []


def test_user_cannot_read_upload_owned_by_another_user(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    with TestClient(app) as client:
        created = client.post(
            "/api/uploads",
            headers=auth_headers(app, username="alice"),
            files={"file": ("evidence.txt", b"safe content", "text/plain")},
        )
        response = client.get(
            f"/api/uploads/{created.json()['id']}",
            headers=auth_headers(app, username="bob"),
        )

    assert created.status_code == 201
    assert response.status_code == 403