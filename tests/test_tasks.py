from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth_headers_for_client, create_task


def test_create_and_list_tasks_for_owner(client: TestClient) -> None:
    created = create_task(client, username="alice", title="Implement validation")

    response = client.get(
        "/api/tasks",
        headers=auth_headers_for_client(client, username="alice"),
    )

    assert response.status_code == 200
    assert response.json()[0]["id"] == created["id"]
    assert response.json()[0]["owner_username"] == "alice"


def test_user_does_not_list_other_user_tasks(client: TestClient) -> None:
    create_task(client, username="alice", title="Alice task")
    create_task(client, username="bob", title="Bob task")

    response = client.get(
        "/api/tasks",
        headers=auth_headers_for_client(client, username="alice"),
    )

    assert response.status_code == 200
    assert [task["owner_username"] for task in response.json()] == ["alice"]


def test_rejects_unexpected_payload_fields(client: TestClient) -> None:
    response = client.post(
        "/api/tasks",
        headers=auth_headers_for_client(client, username="alice"),
        json={
            "title": "Task",
            "description": "Description",
            "status": "TODO",
            "priority": "LOW",
            "owner_id": 999,
        },
    )

    assert response.status_code == 422


def test_rejects_invalid_task_status(client: TestClient) -> None:
    response = client.post(
        "/api/tasks",
        headers=auth_headers_for_client(client, username="alice"),
        json={
            "title": "Task",
            "description": "Description",
            "status": "DONE'; DROP TABLE tasks; --",
            "priority": "LOW",
        },
    )

    assert response.status_code == 422


def test_update_task_requires_owner(client: TestClient) -> None:
    created = create_task(client, username="alice")

    response = client.patch(
        f"/api/tasks/{created['id']}",
        headers=auth_headers_for_client(client, username="bob"),
        json={"status": "DONE"},
    )

    assert response.status_code == 403


def test_delete_task_requires_owner(client: TestClient) -> None:
    created = create_task(client, username="alice")

    response = client.delete(
        f"/api/tasks/{created['id']}",
        headers=auth_headers_for_client(client, username="bob"),
    )

    assert response.status_code == 403