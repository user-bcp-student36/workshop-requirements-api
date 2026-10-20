# Pruebas de la API FastAPI

## Matriz por endpoint

El contrato de referencia es [ENDPOINTS.md](ENDPOINTS.md). Ese documento conserva
la descripcion anterior al refactor: no enumera el 403 de owner ni los limites
y rechazos de archivos actuales. Las filas marcadas **seguridad existente**
verifican la politica ya acordada en [HALLAZGOS.md](../HALLAZGOS.md), no un
contrato nuevo. No se modificaron endpoints ni codigo de produccion.

| endpoint | caso | tipo | resultado esperado |
|---|---|---|---|
| GET /api/tasks | Identidad student, datos iniciales | Camino feliz | 200; ids 1 y 2 en orden ascendente; campos y fecha del contrato |
| GET /api/tasks | Identidad sin tareas | Borde | 200; lista vacia |
| GET /api/tasks | owner omitido, vacio o igual a la identidad; student y trainer | Borde | 200; solo tareas propias |
| GET /api/tasks | Expiracion exactamente igual al reloj fijado | Borde | 200; igualdad temporal aceptada |
| GET /api/tasks | Token ausente, malformado, vencido, secreto incorrecto o expiracion no entera | Error | 401; detail empieza con Invalid token: |
| GET /api/tasks | student consulta trainer y trainer consulta student | Error; seguridad existente | 403; Owner does not match authenticated identity; no expone tareas ajenas |
| GET /api/tasks | Identidad con comillas o texto similar a SQL | Borde; seguridad existente | 200; valores literales, sin acceder a otro owner |
| POST /api/tasks | Titulo, descripcion, estado y prioridad validos | Camino feliz | 201; tarea con owner autenticado; resumen actualizado |
| POST /api/tasks | Objeto vacio | Borde | 201; title y description vacios, status TODO, priority MEDIUM |
| POST /api/tasks | Numeros, null, booleanos, campos extra y valores CUSTOM | Borde | 201; conversion str de campos, extras ignorados, sin enums inventados |
| POST /api/tasks | owner omitido o propio | Borde | 201; owner de la identidad |
| POST /api/tasks | Reiniciar instancia con la misma base temporal | Borde | La tarea persiste y mantiene su contrato |
| POST /api/tasks | Token ausente, malformado, vencido, secreto incorrecto o expiracion no entera, con JSON valido | Error | 401; no inserta tareas |
| POST /api/tasks | Cuerpo ausente, lista, string, numero o JSON malformado | Error | 422; detail es lista de validacion; no inserta tareas |
| POST /api/tasks | owner ajeno en ambas direcciones | Error; seguridad existente | 403; tareas ajenas sin cambios; repositorio no invocado por el servicio |
| POST /api/tasks | SQLite rechaza INSERT mediante trigger temporal | Error; seguridad existente | 500; Task storage error; rollback comprobado en prueba de repositorio |
| POST /api/tasks | Comillas en identidad, titulo y descripcion | Borde; seguridad existente | 201; valores conservados literalmente |
| GET /api/summary | Datos validos y estados TODO, IN_PROGRESS, DONE, ARCHIVED y CUSTOM | Camino feliz | 200; conteos exactos; HIGH excluye DONE y ARCHIVED de highPriorityOpen |
| GET /api/summary | Identidad sin tareas | Borde | 200; total 0, byStatus {}, highPriorityOpen 0 |
| GET /api/summary | owner omitido, vacio o propio; student y trainer | Borde | 200; owner y conteos propios |
| GET /api/summary | Token ausente, malformado, vencido, secreto incorrecto o expiracion no entera | Error | 401; detail empieza con Invalid token: |
| GET /api/summary | owner ajeno en ambas direcciones | Error; seguridad existente | 403; no expone conteos ajenos |
| POST /api/requirements | Archivo .txt, .md, .pdf o .TXT valido | Camino feliz | 201; owner, fileName, storedAt y size; bytes persistidos |
| POST /api/requirements | Archivo vacio | Borde | 201; size 0 y archivo vacio persistido |
| POST /api/requirements | Archivo sin extension | Borde/error; seguridad existente | 415; File extension not allowed; no crea archivos |
| POST /api/requirements | Archivo de exactamente 5 MiB sin Content-Length | Borde; seguridad existente | 201; size y bytes exactos |
| POST /api/requirements | Archivo de 5 MiB + 1 byte sin Content-Length | Error; seguridad existente | 413; File exceeds upload limit; no quedan archivos |
| POST /api/requirements | Token ausente, malformado, vencido, secreto incorrecto o expiracion no entera, con archivo valido | Error | 401; no publica archivos |
| POST /api/requirements | Campo file ausente o texto en vez de archivo | Error | 422; detail es lista de validacion |
| POST /api/requirements | Traversal, ruta absoluta, nombre reservado, colon, comodin o punto/espacio final | Error; seguridad existente | 400; Invalid file name; sin escrituras fuera del directorio |
| POST /api/requirements | Extension .exe | Error; seguridad existente | 415; File extension not allowed |
| POST /api/requirements | Nombre ya existente | Error; seguridad existente | 409; File already exists; contenido original intacto |
| POST /api/requirements | Dos cargas concurrentes con igual nombre | Borde/error; seguridad existente | Una carga correcta y una 409; sin temporales residuales |
| POST /api/requirements | Destino enlazado mediante hardlink | Error; seguridad existente | 409; archivo original no sobrescrito |
| POST /api/requirements | Symlink hacia fuera del directorio | Error; seguridad existente | 400; destino original intacto; omitido solo si SO no permite crear symlink |
| POST /api/requirements | Fallo de escritura o publicacion simulado | Error; seguridad existente | 500; limpieza de temporales; escritura devuelve Upload storage error |
| GET /api/backend-health | Backend remoto 200 y cuerpo UTF-8 | Camino feliz | HTTP local 200; requestedBy, status 200 y cuerpo remoto exactos |
| GET /api/backend-health | Backend remoto 204 con cuerpo vacio | Borde | HTTP local 200; status 204, body vacio |
| GET /api/backend-health | Backend remoto 503 | Error remoto | HTTP local 200; status 503, body unavailable |
| GET /api/backend-health | Timeout simulado | Error remoto | HTTP local 200; status 0 y texto de la excepcion |
| GET /api/backend-health | Token ausente, malformado, vencido, secreto incorrecto o expiracion no entera | Error | 401; detail empieza con Invalid token: |

El 422 generico citado en ENDPOINTS.md se comprueba en los dos POST que tienen
cuerpo obligatorio. Los GET solo declaran strings opcionales o ningun
parametro de entrada validable; no se inventa un 422 para ellos. Un fallo remoto
de health no es un HTTP 500 local. Todas las llamadas remotas se sustituyen con
Mock: se comprueban URL configurada/predeterminada, timeout 3.0 y ausencia de
token reenviado mediante la llamada exacta.

## Codigo de los tests

Fuente ejecutable: [tests/test_api.py](../tests/test_api.py). El bloque siguiente
reproduce ese archivo completo, incluidas las regresiones anteriores y las
pruebas de servicio/repositorio que respaldan los efectos observables de las
rutas. Las fixtures usan SQLite y directorios temporales; no dependen del
backend Quarkus ni de datos de produccion.

```python
import base64
import asyncio
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path
import sqlite3
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from fastapi import UploadFile

from app.main import create_app


def token(username: str = "student", role: str = "STUDENT") -> str:
    raw = f"{username}|{role}|{int(time.time()) + 3600}|WORKSHOP_SECRET_2026"
    return base64.b64encode(raw.encode()).decode()


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
@pytest.mark.parametrize("token_case", ["missing", "malformed", "expired", "wrong-secret", "invalid-expiry"])
def test_endpoint_authentication_errors(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, method: str, path: str, token_case: str,
) -> None:
    monkeypatch.setattr("app.main.time.time", lambda: 2_000_000_000)
    raw_tokens = {
        "expired": "student|STUDENT|1999999999|WORKSHOP_SECRET_2026",
        "wrong-secret": "student|STUDENT|2000000001|wrong-secret",
        "invalid-expiry": "student|STUDENT|not-an-integer|WORKSHOP_SECRET_2026",
    }
    request_headers = {}
    if token_case != "missing":
        encoded = "invalid" if token_case == "malformed" else base64.b64encode(raw_tokens[token_case].encode()).decode()
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
    monkeypatch.setattr("app.main.time.time", lambda: 2_000_000_000)
    encoded = base64.b64encode(b"student|STUDENT|2000000000|WORKSHOP_SECRET_2026").decode()
    response = client.get("/api/tasks", headers={"Authorization": f"Bearer {encoded}"})
    assert response.status_code == 200
    assert len(response.json()) == 2


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
```

## Ejecucion y cobertura

Desde la raiz de este repositorio, con las dependencias de requirements.txt y
requirements-dev.txt instaladas en el entorno virtual (Python 3.13):

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_api.py --cov=app --cov=tests --cov-report=term-missing --cov-report=json:.pytest_cache/testing-coverage.json --cov-fail-under=85
```

En Linux/macOS, sustituir el ejecutable por `.venv/bin/python`.
La configuracion de [pyproject.toml](../pyproject.toml) activa cobertura de
ramas. Se miden API y tests por separado en el informe JSON, ademas del total;
la cobertura de los tests no se usa para ocultar huecos en la API.

Ejecucion verificada el 2026-10-06, Windows, Python 3.13.16:

- 37 casos nuevos aprobados en la ejecucion focalizada (`-k endpoint`).
- Suite completa: **98 passed, 1 skipped**. El unico skip corresponde al
  symlink real, no permitido por este sistema; no se solicitaron privilegios.
- Cobertura total de lineas y ramas: **98.83%**, superior al 85% de
    [REGLAS.md](../REGLAS.md). Por separado, **API 98.53%** y **archivo de tests
    modificado 99.03%**; ambos superan individualmente el 85%. main, modelos,
    servicios y almacenamiento de cargas estan al 100%; repositorio al 89%
    (las cuatro lineas sin ejecutar de tests son posteriores al skip de symlink).
- Advertencias preexistentes de deprecacion de `on_event` y BlockingPortal;
  no son fallos de la suite ni se silencian.

## Riesgos y discrepancias separados

- ENDPOINTS.md describe el estado anterior al refactor. No incluye los
  rechazos de owner, archivos y almacenamiento actuales. Se registra aparte
  en [HALLAZGOS.md](../HALLAZGOS.md); no se reescribe el contrato para obtener
  pruebas verdes.
- H-03 sigue pendiente: el 413 demuestra limite de la copia posterior al
  parseo, no rechazo temprano antes del spool multipart. Estas pruebas no
  prueban limites de recepcion ni de partes adicionales; no se considera
  corregido el riesgo existente.
- H-01 sigue pendiente: aislamiento significa que una identidad student no
  consulta owner trainer; no demuestra autenticidad del token Base64 ni
  impide falsificar la identidad mediante el secreto del laboratorio.
- No se modifico ninguna expectativa previa para acomodar un bug. Las
  pruebas nuevas pasaron contra la implementacion existente, sin parches
  de produccion ni llamadas de red reales.

## Documentos consultados

- [ENDPOINTS.md](ENDPOINTS.md): rutas, formatos y errores del contrato publicado.
- [REGLAS.md](../REGLAS.md): cobertura minima del 85% y restricciones.
- [HALLAZGOS.md](../HALLAZGOS.md): politica de seguridad existente y riesgos pendientes.
- [README.md](../README.md): ejecucion local y version de Python.
- [pyproject.toml](../pyproject.toml): pytest y cobertura de ramas.
- [requirements.txt](../requirements.txt) y [requirements-dev.txt](../requirements-dev.txt): dependencias.
- [CI](../.github/workflows/ci.yml): comando de pruebas y Python 3.13.