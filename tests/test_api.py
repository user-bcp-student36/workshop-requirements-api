from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas import Role
from app.security import create_access_token


def auth_headers(app: Any, username: str = "student", role: Role = Role.STUDENT) -> dict[str, str]:
    token = create_access_token(
        secret=app.state.settings.jwt_secret,
        subject=username,
        role=role,
        issuer=app.state.settings.token_issuer,
    )
    return {"Authorization": f"Bearer {token}"}


def legacy_base64_headers(username: str = "student", role: str = "STUDENT") -> dict[str, str]:
    raw = f"{username}|{role}|{int(time.time()) + 3600}|WORKSHOP_SECRET_2026"
    token = base64.b64encode(raw.encode()).decode()
    return {"Authorization": f"Bearer {token}"}


def test_lists_seeded_tasks_for_owner(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=auth_headers(app))

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert {task["owner"] for task in response.json()} == {"student"}


def test_rejects_legacy_base64_token(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=legacy_base64_headers())

    assert response.status_code == 401


def test_rejects_invalid_token(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": "Bearer invalid"})

    assert response.status_code == 401


def test_creates_task_and_summary(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    with TestClient(app) as client:
        created = client.post(
            "/api/tasks",
            headers=auth_headers(app),
            json={
                "title": "Add tests",
                "description": "Improve coverage",
                "status": "TODO",
                "priority": "HIGH",
            },
        )
        summary = client.get("/api/summary", headers=auth_headers(app))

    assert created.status_code == 201
    assert created.json()["owner"] == "student"
    assert summary.status_code == 200
    assert summary.json()["total"] == 3


def test_rejects_unexpected_task_payload_fields(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    with TestClient(app) as client:
        response = client.post(
            "/api/tasks",
            headers=auth_headers(app),
            json={
                "title": "Unexpected",
                "description": "Extra field should be rejected",
                "status": "TODO",
                "priority": "LOW",
                "owner": "attacker",
            },
        )

    assert response.status_code == 422


def test_prevents_cross_owner_task_access(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    with TestClient(app) as client:
        created = client.post(
            "/api/tasks",
            headers=auth_headers(app, username="alice"),
            json={"title": "Private task", "description": "Owned by Alice"},
        )
        task_id = created.json()["id"]

        forbidden = client.get(
            f"/api/tasks/{task_id}",
            headers=auth_headers(app, username="bob"),
        )

    assert created.status_code == 201
    assert forbidden.status_code == 404


def test_admin_can_access_other_users_tasks(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    with TestClient(app) as client:
        created = client.post(
            "/api/tasks",
            headers=auth_headers(app, username="alice"),
            json={"title": "Admin visible task", "description": "Owned by Alice"},
        )
        task_id = created.json()["id"]

        response = client.get(
            f"/api/tasks/{task_id}",
            headers=auth_headers(app, username="admin", role=Role.ADMIN),
        )

    assert response.status_code == 200
    assert response.json()["owner"] == "alice"


def test_sql_injection_like_owner_does_not_bypass_scope(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    with TestClient(app) as client:
        response = client.get(
            "/api/tasks",
            headers=auth_headers(app, username="student' OR '1'='1"),
        )

    assert response.status_code == 200
    assert response.json() == []


def test_uploads_requirement_with_random_stored_filename(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))

    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=auth_headers(app),
            files={"file": ("requirements.txt", b"Login must be accessible", "text/plain")},
        )

    body = response.json()

    assert response.status_code == 201
    assert body["owner"] == "student"
    assert body["original_filename"] == "requirements.txt"
    assert body["stored_filename"] != "requirements.txt"
    assert (upload_dir / body["stored_filename"]).exists()
    assert not (upload_dir / "requirements.txt").exists()


def test_rejects_upload_path_traversal(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=auth_headers(app),
            files={"file": ("../requirements.txt", b"bad", "text/plain")},
        )

    assert response.status_code == 400


def test_rejects_dangerous_upload_extension(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=auth_headers(app),
            files={"file": ("shell.sh", b"rm -rf /", "text/x-sh")},
        )

    assert response.status_code == 400


def test_rejects_oversized_upload(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    app.state.requirement_service.max_upload_bytes = 8

    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=auth_headers(app),
            files={"file": ("requirements.txt", b"this is too large", "text/plain")},
        )

    assert response.status_code == 413