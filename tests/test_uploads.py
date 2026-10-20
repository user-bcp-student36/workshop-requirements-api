from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from tests.conftest import auth_headers_for_client, create_task


def test_upload_rejects_path_traversal_filename(client: TestClient) -> None:
    task = create_task(client, username="alice")

    response = client.post(
        "/api/uploads",
        headers=auth_headers_for_client(client, username="alice"),
        data={"task_id": str(task["id"])},
        files={"file": ("../evil.txt", b"safe text", "text/plain")},
    )

    assert response.status_code == 400


def test_upload_rejects_dangerous_extension(client: TestClient) -> None:
    task = create_task(client, username="alice")

    response = client.post(
        "/api/uploads",
        headers=auth_headers_for_client(client, username="alice"),
        data={"task_id": str(task["id"])},
        files={"file": ("payload.sh", b"echo unsafe", "text/x-shellscript")},
    )

    assert response.status_code == 400


def test_upload_rejects_oversized_file(client: TestClient) -> None:
    task = create_task(client, username="alice")
    max_bytes = client.app.state.settings.max_upload_bytes

    response = client.post(
        "/api/uploads",
        headers=auth_headers_for_client(client, username="alice"),
        data={"task_id": str(task["id"])},
        files={"file": ("large.txt", b"a" * (max_bytes + 1), "text/plain")},
    )

    assert response.status_code == 413


def test_upload_rejects_content_that_does_not_match_extension(client: TestClient) -> None:
    task = create_task(client, username="alice")

    response = client.post(
        "/api/uploads",
        headers=auth_headers_for_client(client, username="alice"),
        data={"task_id": str(task["id"])},
        files={"file": ("image.png", b"not a real png", "image/png")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid PNG file content"


def test_upload_rejects_invalid_json_content(client: TestClient) -> None:
    task = create_task(client, username="alice")

    response = client.post(
        "/api/uploads",
        headers=auth_headers_for_client(client, username="alice"),
        data={"task_id": str(task["id"])},
        files={"file": ("payload.json", b"{invalid json", "application/json")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid JSON file content"


def test_upload_is_saved_with_random_filename_and_owner(client: TestClient, tmp_path: Path) -> None:
    task = create_task(client, username="alice")

    response = client.post(
        "/api/uploads",
        headers=auth_headers_for_client(client, username="alice"),
        data={"task_id": str(task["id"])},
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["original_filename"] == "notes.txt"
    assert body["stored_filename"] != "notes.txt"
    assert body["stored_filename"].endswith(".txt")
    assert body["owner_id"] == task["owner_id"]

    stored_path = client.app.state.settings.upload_dir / body["stored_filename"]
    assert stored_path.exists()
    assert stored_path.read_bytes() == b"hello"


def test_user_cannot_upload_to_task_owned_by_another_user(client: TestClient) -> None:
    task = create_task(client, username="alice")

    response = client.post(
        "/api/uploads",
        headers=auth_headers_for_client(client, username="bob"),
        data={"task_id": str(task["id"])},
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 403


def test_user_cannot_read_upload_owned_by_another_user(client: TestClient) -> None:
    task = create_task(client, username="alice")
    upload = client.post(
        "/api/uploads",
        headers=auth_headers_for_client(client, username="alice"),
        data={"task_id": str(task["id"])},
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert upload.status_code == 201

    response = client.get(
        f"/api/uploads/{upload.json()['id']}",
        headers=auth_headers_for_client(client, username="bob"),
    )

    assert response.status_code == 403