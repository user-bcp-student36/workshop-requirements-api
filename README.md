# Workshop Requirements API — Python FastAPI

> **Laboratorio intencionalmente vulnerable.** Ejecutar únicamente en local, repositorios privados y ambientes aislados. No publicar en Internet ni desplegar en CERT/PROD.

API FastAPI que administra tareas del workshop y recibe archivos de requerimientos. Usa SQLite y consume el token emitido por el backend Quarkus.

## Ejecución

Requisitos: Python 3.13.

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Swagger: `http://localhost:8000/docs`

## Configuracion del token firmado

La API solo acepta JWT RS256 del emisor acordado. Configurar
`AUTH_TOKEN_PUBLIC_KEY_LOCATION` con una ruta local a la clave publica RSA PEM
del emisor, `AUTH_TOKEN_ISSUER` y `AUTH_TOKEN_AUDIENCE`. Emisor y audiencia deben
coincidir con Java; no proporcionar la clave privada al consumidor.
La configuracion se carga por instancia de app; cambiarla requiere reiniciar.
Si falta o es invalida, las rutas protegidas rechazan el acceso con HTTP 401.

Se validan firma, `iss`, `aud`, `sub`, `groups` con un unico rol y `exp` entero.
Se rechaza cuando la hora actual es mayor o igual a `exp`, sin tolerancia.
No se aceptan tokens legacy ni hay fallback: coordinar el corte con Java y
solicitar nuevo login para sesiones anteriores. El encabezado Bearer y las
operaciones protegidas permanecen. Contrato y evidencia de esta correccion:
[docs/PR-ISSUE-1.md](docs/PR-ISSUE-1.md).

## Endpoints

- `GET /api/tasks`
- `POST /api/tasks`
- `GET /api/summary`
- `POST /api/requirements`
- `GET /api/backend-health`

La rama `main` contiene autenticación débil, SQL concatenado, manejo inseguro de nombres de archivo, conexión global, lógica monolítica y dependencias con CVEs.
