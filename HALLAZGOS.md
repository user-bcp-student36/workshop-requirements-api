# Hallazgos — API Python FastAPI (workshop-requirements-api)

> Todos los hallazgos están en estado `CANDIDATO` y requieren revisión humana antes de abrir issues o cambiar código.

### Escritura de archivos con nombre de upload sin sanear
- Estado: CANDIDATO
- Evidencia: [main.py](app/main.py#L109-L110) construye la ruta con `Path(selected_uploads) / str(file.filename)` y escribe el contenido sin validar el nombre.
- Impacto: un nombre de archivo con separadores de ruta puede escribir fuera del directorio de uploads.
- Prioridad propuesta: Alta.
- Contrato potencialmente afectado: `POST /api/requirements` (respuesta `{owner, fileName, storedAt, size}`), probado en [test_api.py](tests/test_api.py).
- Cómo validarlo: añadir una prueba que envíe un `filename` con `../` y compruebe que el archivo no se crea fuera de `uploads`. Tras la corrección, la respuesta debe ser un error de validación o el nombre debe quedar normalizado dentro del directorio.

### Consultas SQL concatenadas con parámetros de usuario
- Estado: CANDIDATO
- Evidencia: [main.py](app/main.py#L70) concatena `requested_owner` en `WHERE owner='...'`. [main.py](app/main.py#L84) concatena `title`, `description`, `status`, `owner` y `priority` en el `INSERT`. [main.py](app/main.py#L93) repite el patrón en `/api/summary`.
- Impacto: un valor con comillas altera la consulta. Puede exponer o modificar datos de la tabla `tasks`.
- Prioridad propuesta: Alta.
- Contrato potencialmente afectado: `GET /api/tasks?owner=`, `POST /api/tasks`, `GET /api/summary?owner=`.
- Cómo validarlo: prueba con un `owner` que contenga comillas simples. Si responde 500 o devuelve filas inesperadas, se confirma. Tras la corrección, debe usarse `?` como parámetro y la respuesta debe ser 200 con lista vacía.

### Autorización: el parámetro owner sustituye la identidad del token
- Estado: CANDIDATO
- Evidencia: [main.py](app/main.py#L69) usa `owner or identity["username"]`, de modo que el parámetro de consulta tiene prioridad sobre el usuario autenticado. Lo mismo ocurre en [main.py](app/main.py#L92) para `/api/summary`. El `owner` del `POST` ([main.py](app/main.py#L83)) también se toma del payload.
- Impacto: cualquier usuario con token válido puede leer tareas y resúmenes de otro usuario, por ejemplo `trainer`.
- Prioridad propuesta: Alta.
- Contrato potencialmente afectado: `GET /api/tasks` y `GET /api/summary`. El frontend envía `owner` igual al usuario autenticado ([dashboard.component.ts](../workshop-login-frontend/src/app/dashboard/dashboard.component.ts#L43)), así que usar solo la identidad del token no lo rompe.
- Cómo validarlo: con un token de `student`, pedir `GET /api/tasks?owner=trainer`. Si devuelve la tarea "Trainer notes", se confirma. Tras la corrección, debe devolver solo tareas de `student` o rechazar el parámetro.

### Firma del token compartida y sin verificación de integridad
- Estado: CANDIDATO
- Evidencia: [main.py](app/main.py#L14) define `LEGACY_SECRET = "WORKSHOP_SECRET_2026"`, el mismo secreto que [LegacyTokenUtil.java](../workshop-auth-backend/src/main/java/com/bcp/workshop/auth/LegacyTokenUtil.java#L8). [main.py](app/main.py#L19-L22) decodifica el token en base64 y compara el secreto en texto plano.
- Impacto: quien conozca el secreto puede fabricar tokens con cualquier usuario y rol. Cualquier cambio del formato debe coordinarse con el backend Quarkus.
- Prioridad propuesta: Alta.
- Contrato potencialmente afectado: header `Authorization: Bearer` de todos los endpoints `/api/*` y el formato del token emitido por `POST /auth/login`.
- Cómo validarlo: decodificar un token real de login y comprobar que contiene el secreto. Tras la corrección, el secreto no debe estar en el código y la validación debe verificar firma y expiración.

### Detalles internos en las respuestas de error
- Estado: CANDIDATO
- Evidencia: [main.py](app/main.py#L26) devuelve `"Invalid token: " + str(error)` en el `detail` del 401. [main.py](app/main.py#L121) devuelve `str(error)` en `body` de `/api/backend-health`, con `status: 0`.
- Impacto: el cliente recibe texto de excepciones internas, lo que facilita el diagnóstico de un atacante.
- Prioridad propuesta: Media.
- Contrato potencialmente afectado: `detail` de los 401 en `/api/*` y el campo `body` de `GET /api/backend-health`.
- Cómo validarlo: `Invoke-RestMethod` con un token mal formado contra `/api/tasks` y revisar el `detail`. Tras la corrección, debe devolverse un mensaje genérico y registrar el detalle en logs.

### CORS con comodín y credenciales habilitadas
- Estado: CANDIDATO
- Evidencia: [main.py](app/main.py#L50-L51) configura `allow_origins=["*"]` junto con `allow_credentials=True`.
- Impacto: cualquier origen puede hacer peticiones al API desde el navegador. La combinación es contradictoria para el estándar CORS, y el comportamiento real depende de la versión de Starlette.
- Prioridad propuesta: Media.
- Contrato potencialmente afectado: todos los endpoints `/api/*` consumidos desde el frontend en `http://localhost:4200`.
- Cómo validarlo: `curl -i -X OPTIONS http://127.0.0.1:8000/api/tasks -H "Origin: https://sitio-externo.example" -H "Access-Control-Request-Method: GET"` y revisar `Access-Control-Allow-Origin`. Tras la corrección, solo deben aparecer los orígenes del frontend.
