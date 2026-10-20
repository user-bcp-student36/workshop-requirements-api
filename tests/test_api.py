import base64
import asyncio
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path
import sqlite3
from unittest.mock import Mock

import pytest
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from fastapi import UploadFile

from app.main import create_app

TEST_ISSUER = "https://auth.test.invalid"
TEST_AUDIENCE = "requirements-test"
TEST_SIGNING_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(autouse=True)
def signing_configuration(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    public_key = tmp_path_factory.mktemp("jwt-trust") / "verification.pem"
    public_key.write_bytes(TEST_SIGNING_KEY.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo,
    ))
    monkeypatch.setenv("AUTH_TOKEN_PUBLIC_KEY_LOCATION", str(public_key))
    monkeypatch.setenv("AUTH_TOKEN_ISSUER", TEST_ISSUER)
    monkeypatch.setenv("AUTH_TOKEN_AUDIENCE", TEST_AUDIENCE)


def token_claims(username: str = "student", role: str = "STUDENT") -> dict:
    return {"sub": username, "groups": [role], "iss": TEST_ISSUER, "aud": TEST_AUDIENCE, "exp": int(time.time()) + 3600}


def token(username: str = "student", role: str = "STUDENT") -> str:
    return jwt.encode(token_claims(username, role), TEST_SIGNING_KEY, algorithm="RS256")


def headers(username: str = "student", role: str = "STUDENT") -> dict[str, str]:
    return {"Authorization": f"Bearer {token(username, role)}"}


def test_lists_seeded_tasks(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_creates_task_and_summary(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        created = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": "Add tests", "description": "Improve coverage", "status": "TODO", "priority": "HIGH"},
        )
        summary = client.get("/api/summary", headers=headers())
    assert created.status_code == 201
    assert created.json()["owner"] == "student"
    assert summary.json()["total"] == 3


def test_uploads_requirement(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.txt", b"Login must be accessible", "text/plain")},
        )
    assert response.status_code == 201
    assert (upload_dir / "requirements.txt").exists()


def test_rejects_invalid_token(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401


@pytest.fixture
def client(tmp_path: Path):
    application = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(application) as test_client:
        yield test_client


def assert_task_contract(task: dict) -> None:
    assert set(task) == {"id", "title", "description", "status", "owner", "priority", "createdAt"}
    assert isinstance(task["id"], int)
    assert all(isinstance(value, str) for key, value in task.items() if key != "id")
    datetime.strptime(task["createdAt"], "%Y-%m-%d %H:%M:%S")


def test_characterization_seeded_contract(client: TestClient) -> None:
    response = client.get("/api/tasks", headers=headers())
    assert response.status_code == 200
    tasks = response.json()
    assert [task["id"] for task in tasks] == [1, 2]
    assert [task["title"] for task in tasks] == ["Refactor login", "Review API"]
    assert [task["status"] for task in tasks] == ["TODO", "IN_PROGRESS"]
    assert [task["priority"] for task in tasks] == ["HIGH", "MEDIUM"]
    for task in tasks:
        assert task["owner"] == "student"
        assert_task_contract(task)


@pytest.mark.parametrize("payload", [
    {},
    {"title": 42, "description": None, "status": True, "priority": 7, "extra": "ignored"},
    {"title": "", "description": "", "status": "CUSTOM", "priority": "CUSTOM"},
])
def test_characterization_create_values(client: TestClient, payload: dict) -> None:
    response = client.post("/api/tasks", headers=headers(), json=payload)
    assert response.status_code == 201
    task = response.json()
    assert_task_contract(task)
    for field, default in {"title": "", "description": "", "status": "TODO", "priority": "MEDIUM"}.items():
        assert task[field] == str(payload.get(field, default))
    assert task["owner"] == "student"


def test_characterization_summary_rules(client: TestClient) -> None:
    for status, priority in [("DONE", "HIGH"), ("ARCHIVED", "HIGH"), ("TODO", "HIGH"), ("CUSTOM", "HIGH"), ("TODO", "LOW")]:
        response = client.post("/api/tasks", headers=headers(), json={"status": status, "priority": priority})
        assert response.status_code == 201
    response = client.get("/api/summary", headers=headers())
    assert response.status_code == 200
    assert response.json() == {
        "owner": "student", "total": 7,
        "byStatus": {"TODO": 3, "IN_PROGRESS": 1, "DONE": 1, "ARCHIVED": 1, "CUSTOM": 1},
        "highPriorityOpen": 3,
    }
    empty = client.get("/api/summary", headers=headers("new-user"))
    assert empty.json() == {"owner": "new-user", "total": 0, "byStatus": {}, "highPriorityOpen": 0}
    assert client.get("/api/tasks", headers=headers("new-user")).json() == []


@pytest.mark.parametrize("username,role,count", [("student", "STUDENT", 2), ("trainer", "TRAINER", 1)])
@pytest.mark.parametrize("owner", [None, "", "self"])
def test_characterization_own_queries(client: TestClient, username: str, role: str, count: int, owner: str | None) -> None:
    params = {} if owner is None else {"owner": username if owner == "self" else owner}
    tasks = client.get("/api/tasks", headers=headers(username, role), params=params)
    summary = client.get("/api/summary", headers=headers(username, role), params=params)
    assert tasks.status_code == summary.status_code == 200
    assert len(tasks.json()) == count
    assert all(task["owner"] == username for task in tasks.json())
    assert summary.json()["owner"] == username
    assert summary.json()["total"] == count


@pytest.mark.parametrize("owner", [None, "student"])
def test_characterization_own_create(client: TestClient, owner: str | None) -> None:
    payload = {} if owner is None else {"owner": owner}
    response = client.post("/api/tasks", headers=headers(), json=payload)
    assert response.status_code == 201
    assert response.json()["owner"] == "student"


def test_characterization_persistence(tmp_path: Path) -> None:
    database = str(tmp_path / "persistent.db")
    uploads = str(tmp_path / "uploads")
    with TestClient(create_app(database, uploads)) as first_client:
        created = first_client.post("/api/tasks", headers=headers(), json={"title": "Persistent"}).json()
    with TestClient(create_app(database, uploads)) as second_client:
        tasks = second_client.get("/api/tasks", headers=headers()).json()
    assert len(tasks) == 3
    assert tasks[-1] == created


@pytest.mark.parametrize("content", [b"", b"Login must be accessible"])
def test_characterization_upload_contract(client: TestClient, tmp_path: Path, content: bytes) -> None:
    response = client.post("/api/requirements", headers=headers(), files={"file": ("requirements.txt", content, "text/plain")})
    assert response.status_code == 201
    destination = tmp_path / "uploads" / "requirements.txt"
    assert response.json() == {
        "owner": "student", "fileName": "requirements.txt", "storedAt": str(destination), "size": len(content),
    }
    assert destination.read_bytes() == content


def test_characterization_upload_missing_file(client: TestClient) -> None:
    assert client.post("/api/requirements", headers=headers()).status_code == 422


@pytest.mark.parametrize("path", ["/api/tasks", "/api/summary", "/api/backend-health"])
def test_characterization_get_requires_token(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 401
    assert set(response.json()) == {"detail"}


def test_characterization_upload_requires_token(client: TestClient) -> None:
    response = client.post("/api/requirements", files={"file": ("requirements.txt", b"content")})
    assert response.status_code == 401


def test_characterization_openapi_surface(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    expected = {"/api/tasks": {"get", "post"}, "/api/summary": {"get"}, "/api/requirements": {"post"}, "/api/backend-health": {"get"}}
    assert set(schema["paths"]) == set(expected)
    for path, methods in expected.items():
        assert set(schema["paths"][path]) == methods
        for method in methods:
            operation = schema["paths"][path][method]
            assert any(parameter["name"] == "authorization" and parameter["in"] == "header" for parameter in operation["parameters"])
            assert ("201" if method == "post" else "200") in operation["responses"]
    for path in ("/api/tasks", "/api/summary"):
        assert any(parameter["name"] == "owner" and not parameter["required"] for parameter in schema["paths"][path]["get"]["parameters"])
    assert schema["paths"]["/api/tasks"]["post"]["requestBody"]["required"] is True
    assert "application/json" in schema["paths"]["/api/tasks"]["post"]["requestBody"]["content"]
    assert "multipart/form-data" in schema["paths"]["/api/requirements"]["post"]["requestBody"]["content"]


@pytest.mark.parametrize("username", ["student", "O'Brien", "unknown' OR '1'='1"])
def test_security_sql_values_are_literal(client: TestClient, username: str) -> None:
    original = client.get("/api/tasks", headers=headers("trainer", "TRAINER")).json()
    response = client.post("/api/tasks", headers=headers(username), json={
        "title": "Owner's task", "description": "A quote ' and SQL-like text; --", "status": "TODO", "priority": "HIGH",
    })
    assert response.status_code == 201
    created = response.json()
    assert created["title"] == "Owner's task"
    assert created["description"] == "A quote ' and SQL-like text; --"
    tasks = client.get("/api/tasks", headers=headers(username)).json()
    assert created in tasks
    assert all(task["owner"] == username for task in tasks)
    assert client.get("/api/summary", headers=headers(username)).json()["total"] == len(tasks)
    assert client.get("/api/tasks", headers=headers("trainer", "TRAINER")).json() == original


@pytest.mark.parametrize("username,role,other", [("student", "STUDENT", "trainer"), ("trainer", "TRAINER", "student")])
def test_security_owner_isolation(client: TestClient, username: str, role: str, other: str) -> None:
    before = client.get("/api/tasks", headers=headers(other)).json()
    for path in ("/api/tasks", "/api/summary"):
        response = client.get(path, headers=headers(username, role), params={"owner": other})
        assert response.status_code == 403
        assert response.json() == {"detail": "Owner does not match authenticated identity"}
    response = client.post("/api/tasks", headers=headers(username, role), json={"owner": other})
    assert response.status_code == 403
    assert client.get("/api/tasks", headers=headers(other)).json() == before


def test_security_rejected_owner_does_not_call_repository() -> None:
    from app.models import Identity, TaskCreate
    from app.task_service import TaskService
    from fastapi import HTTPException

    repository = Mock()
    service = TaskService(repository)
    identity = Identity(username="student", role="STUDENT")
    for operation in (
        lambda: service.list_tasks("trainer", identity),
        lambda: service.summary("trainer", identity),
        lambda: service.create_task(TaskCreate(owner="trainer"), identity),
    ):
        with pytest.raises(HTTPException) as error:
            operation()
        assert error.value.status_code == 403
    assert repository.mock_calls == []


def test_security_repository_parameters_and_rollback(tmp_path: Path) -> None:
    from app.models import TaskCreate
    from app.task_repository import TaskRepository

    application = create_app(str(tmp_path / "repository.db"), str(tmp_path / "uploads"))
    with TestClient(application):
        connection = application.state.connection
        repository = TaskRepository(connection)
        owner = "unknown' OR '1'='1"
        assert repository.list_for_owner(owner) == []
        assert repository.summary_rows(owner) == []
        created = repository.create(TaskCreate(title="Owner's task"), owner)
        assert repository.get_by_id(created.id) == created
        assert repository.list_for_owner(owner) == [created]
        connection.execute("CREATE TRIGGER reject_task BEFORE INSERT ON tasks BEGIN SELECT RAISE(ABORT, 'internal storage detail'); END")
        with pytest.raises(sqlite3.IntegrityError):
            repository.create(TaskCreate(title="Rejected"), owner)
        assert not connection.in_transaction
        assert repository.list_for_owner(owner) == [created]


def test_security_storage_error_is_generic(client: TestClient) -> None:
    client.app.state.connection.execute("CREATE TRIGGER reject_task BEFORE INSERT ON tasks BEGIN SELECT RAISE(ABORT, 'internal storage detail'); END")
    response = client.post("/api/tasks", headers=headers(), json={"title": "Rejected"})
    assert response.status_code == 500
    assert response.json() == {"detail": "Task storage error"}


@pytest.mark.parametrize("name", ["../outside.txt", "absolute", "CON.txt", "file:stream.txt", "file?.txt", "file.txt ", "file.", ".."])
def test_security_upload_invalid_name(client: TestClient, tmp_path: Path, name: str) -> None:
    if name == "absolute":
        name = (tmp_path / "outside.txt").as_posix()
    response = client.post("/api/requirements", headers=headers(), files={"file": (name, b"untrusted")})
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid file name"}
    assert list((tmp_path / "uploads").iterdir()) == []
    assert not (tmp_path / "outside.txt").exists()


@pytest.mark.parametrize("name", ["requirements.md", "requirements.pdf", "requirements.TXT"])
def test_security_upload_allowed_extensions(client: TestClient, name: str) -> None:
    response = client.post("/api/requirements", headers=headers(), files={"file": (name, b"content")})
    assert response.status_code == 201
    assert response.json()["fileName"] == name


def test_security_upload_extension_rejected(client: TestClient, tmp_path: Path) -> None:
    response = client.post("/api/requirements", headers=headers(), files={"file": ("requirement.exe", b"content")})
    assert response.status_code == 415
    assert response.json() == {"detail": "File extension not allowed"}
    assert list((tmp_path / "uploads").iterdir()) == []


def test_security_upload_collision(client: TestClient, tmp_path: Path) -> None:
    first = client.post("/api/requirements", headers=headers(), files={"file": ("requirements.txt", b"original")})
    second = client.post("/api/requirements", headers=headers(), files={"file": ("requirements.txt", b"replacement")})
    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json() == {"detail": "File already exists"}
    assert (tmp_path / "uploads" / "requirements.txt").read_bytes() == b"original"
    assert len(list((tmp_path / "uploads").iterdir())) == 1


@pytest.mark.parametrize("extra_bytes,expected", [(0, 201), (1, 413)])
def test_security_upload_size_without_content_length(client: TestClient, tmp_path: Path, extra_bytes: int, expected: int) -> None:
    content = b"x" * (5 * 1024 * 1024 + extra_bytes)
    request = client.build_request("POST", "/api/requirements", headers=headers(), files={"file": ("requirements.txt", content)})
    del request.headers["content-length"]
    response = client.send(request)
    assert response.status_code == expected
    destination = tmp_path / "uploads" / "requirements.txt"
    if expected == 201:
        assert response.json()["size"] == len(content)
        assert destination.read_bytes() == content
    else:
        assert response.json() == {"detail": "File exceeds upload limit"}
        assert list((tmp_path / "uploads").iterdir()) == []


@pytest.mark.parametrize("name", [r"..\outside.txt", r"C:\outside.txt", r"C:outside.txt", r"\\server\share\outside.txt", "", "NUL.txt", "bad\x00.txt"])
def test_security_upload_service_rejects_windows_names(tmp_path: Path, name: str) -> None:
    from app.models import Identity
    from app.upload_service import UploadService
    from fastapi import HTTPException

    service = UploadService(str(tmp_path))
    upload = UploadFile(filename=name, file=BytesIO(b"content"))
    with pytest.raises(HTTPException) as error:
        asyncio.run(service.store(upload, Identity(username="student", role="STUDENT")))
    assert error.value.status_code == 400
    assert list(tmp_path.iterdir()) == []


def test_security_upload_write_failure_cleanup(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app import upload_storage

    async def fail_write(*args, **kwargs):
        raise OSError("internal disk detail")

    monkeypatch.setattr(upload_storage, "write_limited_content", fail_write)
    response = client.post("/api/requirements", headers=headers(), files={"file": ("requirements.txt", b"content")})
    assert response.status_code == 500
    assert response.json() == {"detail": "Upload storage error"}
    assert list((tmp_path / "uploads").iterdir()) == []


def test_security_upload_publish_failure_cleanup(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app import upload_storage

    def fail_publish(*args, **kwargs):
        raise OSError("internal publication detail")

    monkeypatch.setattr(upload_storage.os, "link", fail_publish)
    response = client.post("/api/requirements", headers=headers(), files={"file": ("requirements.txt", b"content")})
    assert response.status_code == 500
    assert list((tmp_path / "uploads").iterdir()) == []


def test_security_upload_containment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.models import Identity
    from app.upload_service import UploadService
    from fastapi import HTTPException

    directory = tmp_path / "uploads"
    directory.mkdir()
    outside = tmp_path / "outside.txt"
    original_resolve = Path.resolve

    def resolve_destination(path: Path, *args, **kwargs):
        if path == directory / "requirements.txt":
            return outside
        return original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", resolve_destination)
    upload = UploadFile(filename="requirements.txt", file=BytesIO(b"content"))
    with pytest.raises(HTTPException) as error:
        asyncio.run(UploadService(str(directory)).store(upload, Identity(username="student", role="STUDENT")))
    assert error.value.status_code == 400
    assert not outside.exists()


def test_security_upload_hardlink_target_not_overwritten(client: TestClient, tmp_path: Path) -> None:
    import os

    outside = tmp_path / "original.txt"
    outside.write_bytes(b"original")
    os.link(outside, tmp_path / "uploads" / "requirements.txt")
    response = client.post("/api/requirements", headers=headers(), files={"file": ("requirements.txt", b"replacement")})
    assert response.status_code == 409
    assert outside.read_bytes() == b"original"


def test_security_upload_concurrent_collision(tmp_path: Path) -> None:
    from app.models import Identity
    from app.upload_service import UploadService
    from fastapi import HTTPException

    service = UploadService(str(tmp_path))
    identity = Identity(username="student", role="STUDENT")

    async def simultaneous_uploads():
        return await asyncio.gather(
            service.store(UploadFile(filename="requirements.txt", file=BytesIO(b"first")), identity),
            service.store(UploadFile(filename="requirements.txt", file=BytesIO(b"second")), identity),
            return_exceptions=True,
        )

    results = asyncio.run(simultaneous_uploads())
    successes = [result for result in results if not isinstance(result, BaseException)]
    failures = [result for result in results if isinstance(result, HTTPException)]
    assert len(successes) == len(failures) == 1
    assert failures[0].status_code == 409
    assert (tmp_path / "requirements.txt").read_bytes() in (b"first", b"second")
    assert list(tmp_path.iterdir()) == [tmp_path / "requirements.txt"]


def test_security_upload_symlink_destination(client: TestClient, tmp_path: Path) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"original")
    destination = tmp_path / "uploads" / "requirements.txt"
    try:
        destination.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"Operating system cannot create symlinks: {error}")
    response = client.post("/api/requirements", headers=headers(), files={"file": ("requirements.txt", b"replacement")})
    assert response.status_code == 400
    assert destination.is_symlink()
    assert outside.read_bytes() == b"original"


@pytest.mark.parametrize("method,path", [
    ("GET", "/api/tasks"),
    ("POST", "/api/tasks"),
    ("GET", "/api/summary"),
    ("POST", "/api/requirements"),
    ("GET", "/api/backend-health"),
])
@pytest.mark.parametrize("token_case", ["missing", "malformed", "expired", "legacy", "invalid-expiry"])
def test_endpoint_authentication_errors(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, method: str, path: str, token_case: str,
) -> None:
    monkeypatch.setattr("app.auth_token.time.time", lambda: 2_000_000_000)
    claims = token_claims()
    claims["exp"] = "not-an-integer" if token_case == "invalid-expiry" else 1_999_999_999
    request_headers = {}
    if token_case != "missing":
        encoded = jwt.encode(claims, TEST_SIGNING_KEY, algorithm="RS256")
        if token_case == "malformed":
            encoded = "invalid"
        elif token_case == "legacy":
            legacy = "student|STUDENT|2000000001|" + "WORKSHOP_SECRET_2026"
            encoded = base64.b64encode(legacy.encode()).decode()
        request_headers = {"Authorization": f"Bearer {encoded}"}
    request_options = {}
    if method == "POST":
        request_options = {"json": {}} if path == "/api/tasks" else {"files": {"file": ("requirements.txt", b"content")}}
    response = client.request(method, path, headers=request_headers, **request_options)
    assert response.status_code == 401
    assert set(response.json()) == {"detail"}
    assert response.json()["detail"].startswith("Invalid token: ")
    assert client.app.state.connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 3
    assert list(Path(client.app.state.upload_dir).iterdir()) == []


def test_endpoint_token_expiry_equality(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.auth_token.time.time", lambda: 2_000_000_000)
    claims = token_claims()
    claims["exp"] = 2_000_000_000
    encoded = jwt.encode(claims, TEST_SIGNING_KEY, algorithm="RS256")
    response = client.get("/api/tasks", headers={"Authorization": f"Bearer {encoded}"})
    assert response.status_code == 401


@pytest.mark.parametrize("method,path", [
    ("GET", "/api/tasks"), ("POST", "/api/tasks"), ("GET", "/api/summary"),
    ("POST", "/api/requirements"), ("GET", "/api/backend-health"),
])
@pytest.mark.parametrize("case", [
    "identity", "role", "expiration", "wrong-key", "unsigned", "symmetric",
    "wrong-issuer", "wrong-audience", "missing-issuer", "missing-audience", "missing-expiration",
])
def test_jwt_rejects_untrusted_claims_before_operations(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, method: str, path: str, case: str,
) -> None:
    import json

    claims = token_claims()
    encoded = jwt.encode(claims, TEST_SIGNING_KEY, algorithm="RS256")
    if case in {"identity", "role", "expiration"}:
        field, value = {"identity": ("sub", "trainer"), "role": ("groups", ["TRAINER"]), "expiration": ("exp", 4_000_000_000)}[case]
        claims[field] = value
        parts = encoded.split(".")
        parts[1] = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
        encoded = ".".join(parts)
    elif case == "wrong-key":
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        encoded = jwt.encode(claims, other_key, algorithm="RS256")
    elif case == "unsigned":
        encoded = jwt.encode(claims, None, algorithm="none")
    elif case == "symmetric":
        encoded = jwt.encode(claims, b"synthetic-test-only-key-material-32", algorithm="HS256")
    else:
        if case == "wrong-issuer":
            claims["iss"] = "https://other.test.invalid"
        elif case == "wrong-audience":
            claims["aud"] = "other-test"
        else:
            del claims[{"missing-issuer": "iss", "missing-audience": "aud", "missing-expiration": "exp"}[case]]
        encoded = jwt.encode(claims, TEST_SIGNING_KEY, algorithm="RS256")
    network = Mock(side_effect=AssertionError("Rejected identity must not reach backend"))
    monkeypatch.setattr("app.main.urllib3.PoolManager", network)
    options = {}
    if method == "POST":
        options = {"json": {"title": "Must not persist"}} if path == "/api/tasks" else {"files": {"file": ("requirements.txt", b"content")}}
    response = client.request(method, path, headers={"Authorization": "Bearer " + encoded}, **options)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token: invalid token"}
    assert client.app.state.connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 3
    assert list(Path(client.app.state.upload_dir).iterdir()) == []
    network.assert_not_called()


@pytest.mark.parametrize("field,value", [
    ("sub", None), ("sub", ""), ("sub", 42), ("groups", None), ("groups", "STUDENT"),
    ("groups", []), ("groups", ["STUDENT", "TRAINER"]), ("groups", [42]), ("groups", [""]),
    ("exp", True), ("exp", "4000000000"), ("exp", 4_000_000_000.0),
])
def test_jwt_rejects_invalid_identity_and_expiration(client: TestClient, field: str, value: object) -> None:
    claims = token_claims()
    claims[field] = value
    encoded = jwt.encode(claims, TEST_SIGNING_KEY, algorithm="RS256")
    assert client.get("/api/tasks", headers={"Authorization": "Bearer " + encoded}).status_code == 401


@pytest.mark.parametrize("scheme", ["", "Basic ", "Bearer  ", "Bearer \t"])
def test_jwt_requires_bearer_header(client: TestClient, scheme: str) -> None:
    assert client.get("/api/tasks", headers={"Authorization": scheme + token()}).status_code == 401


def test_jwt_preserves_identity_role_and_strict_expiration(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.auth_token.time.time", lambda: 2_000_000_000.5)
    claims = token_claims("trainer", "TRAINER")
    claims["exp"] = 2_000_000_001
    encoded = jwt.encode(claims, TEST_SIGNING_KEY, algorithm="RS256")
    assert client.app.state.token_verifier.verify("bearer " + encoded) == {"username": "trainer", "role": "TRAINER"}
    response = client.get("/api/tasks", headers={"Authorization": "Bearer " + encoded})
    assert response.status_code == 200
    assert all(task["owner"] == "trainer" for task in response.json())


@pytest.mark.parametrize("setting", ["AUTH_TOKEN_PUBLIC_KEY_LOCATION", "AUTH_TOKEN_ISSUER", "AUTH_TOKEN_AUDIENCE"])
@pytest.mark.parametrize("value", [None, ""])
def test_jwt_missing_configuration_denies_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, setting: str, value: str | None,
) -> None:
    if value is None:
        monkeypatch.delenv(setting, raising=False)
    else:
        monkeypatch.setenv(setting, value)
    with TestClient(create_app(str(tmp_path / "isolated.db"), str(tmp_path / "isolated-uploads"))) as test_client:
        assert test_client.get("/api/tasks", headers=headers()).status_code == 401


@pytest.mark.parametrize("key_case", ["missing", "malformed", "weak", "non-rsa", "unsupported"])
def test_jwt_invalid_public_key_denies_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, key_case: str,
) -> None:
    from cryptography.exceptions import UnsupportedAlgorithm
    from cryptography.hazmat.primitives.asymmetric import ec

    location = tmp_path / "invalid-public.pem"
    if key_case == "malformed":
        location.write_text("invalid-test-key")
    elif key_case in {"weak", "non-rsa"}:
        key = rsa.generate_private_key(public_exponent=65537, key_size=1024) if key_case == "weak" else ec.generate_private_key(ec.SECP256R1())
        location.write_bytes(key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    elif key_case == "unsupported":
        location.write_text("synthetic-test-key")
        monkeypatch.setattr("app.auth_token.serialization.load_pem_public_key", Mock(side_effect=UnsupportedAlgorithm("test")))
    monkeypatch.setenv("AUTH_TOKEN_PUBLIC_KEY_LOCATION", str(location))
    with TestClient(create_app(str(tmp_path / "isolated.db"), str(tmp_path / "isolated-uploads"))) as test_client:
        assert test_client.get("/api/tasks", headers=headers()).status_code == 401


@pytest.mark.parametrize("body", [None, "[]", '"text"', "42", "{invalid-json"])
def test_endpoint_create_invalid_body(client: TestClient, body: str | None) -> None:
    response = client.post(
        "/api/tasks", headers={**headers(), "Content-Type": "application/json"}, content=body,
    )
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)
    assert client.get("/api/tasks", headers=headers()).json()[0]["id"] == 1
    assert len(client.get("/api/tasks", headers=headers()).json()) == 2


def test_endpoint_upload_without_extension(client: TestClient, tmp_path: Path) -> None:
    response = client.post("/api/requirements", headers=headers(), files={"file": ("requirements", b"content")})
    assert response.status_code == 415
    assert response.json() == {"detail": "File extension not allowed"}
    assert list((tmp_path / "uploads").iterdir()) == []


def test_endpoint_upload_non_file_field(client: TestClient, tmp_path: Path) -> None:
    response = client.post("/api/requirements", headers=headers(), data={"file": "not-a-file"})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)
    assert list((tmp_path / "uploads").iterdir()) == []


@pytest.mark.parametrize("remote_status,remote_body", [(200, b'{"status":"UP"}'), (503, b"unavailable"), (204, b"")])
def test_endpoint_backend_health_responses(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, remote_status: int, remote_body: bytes,
) -> None:
    from app import main

    remote_url = "http://auth.test/q/health"
    monkeypatch.setenv("AUTH_HEALTH_URL", remote_url)
    pool = Mock()
    pool.request.return_value = Mock(status=remote_status, data=remote_body)
    pool_factory = Mock(return_value=pool)
    monkeypatch.setattr(main.urllib3, "PoolManager", pool_factory)
    response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 200
    assert response.json() == {"requestedBy": "student", "status": remote_status, "body": remote_body.decode("utf-8")}
    pool_factory.assert_called_once_with()
    pool.request.assert_called_once_with("GET", remote_url, timeout=3.0)


def test_endpoint_backend_health_connection_error(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app import main

    monkeypatch.delenv("AUTH_HEALTH_URL", raising=False)
    pool = Mock()
    pool.request.side_effect = TimeoutError("backend timeout")
    monkeypatch.setattr(main.urllib3, "PoolManager", Mock(return_value=pool))
    response = client.get("/api/backend-health", headers=headers("trainer", "TRAINER"))
    assert response.status_code == 200
    assert response.json() == {"requestedBy": "trainer", "status": 0, "body": "backend timeout"}
    pool.request.assert_called_once_with("GET", "http://localhost:8080/q/health", timeout=3.0)
