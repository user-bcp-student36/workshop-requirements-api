# Contratos actuales - API FastAPI

Documento generado porque no existia, a partir de `app/main.py` y contrastado
con las pruebas disponibles en `tests/test_api.py`. Describe el comportamiento
actual, no un contrato nuevo ni una propuesta de cambios. El refactor debe
conservar rutas, formatos y nombres de campos; las correcciones de seguridad
se realizan internamente. El seguimiento vive solo en `HALLAZGOS.md`.

## Ejecucion local

Segun `README.md`, se requiere Python 3.13. Desde la raiz de este repositorio,
crear y activar un entorno virtual e instalar `requirements.txt` y
`requirements-dev.txt`. Iniciar con:

```text
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Swagger se publica en `http://localhost:8000/docs`. Laboratorio exclusivamente
local y aislado; no desplegar en Internet ni en produccion.

## Rutas

Todas las rutas siguientes dependen de `legacy_identity` y reciben el header
`Authorization`. Un token invalido genera HTTP 401 con JSON
`{"detail": "Invalid token: <detalle del error>"}` (app/main.py:17, 25, 26).
FastAPI valida los parametros declarados y puede responder HTTP 422 por una
entrada que no cumpla el esquema; no hay manejadores propios para los errores
de SQLite o escritura de archivos.

| Metodo y ruta | Entrada | Respuesta correcta | Evidencia |
|---|---|---|---|
| GET /api/tasks | Query opcional owner, string. Omitido o vacio usa username del token. | HTTP 200, lista de tareas ordenada por id ascendente; lista vacia si no hay coincidencias. | app/main.py:67; app/main.py:68; app/main.py:69; app/main.py:70; app/main.py:75 |
| POST /api/tasks | Objeto JSON. Campos title, description, status, priority y owner opcionales dentro del objeto; el cuerpo es obligatorio. Valores convertidos mediante str. | HTTP 201, objeto de la tarea creada. | app/main.py:77; app/main.py:78; app/main.py:79; app/main.py:80; app/main.py:81; app/main.py:82; app/main.py:83; app/main.py:88 |
| GET /api/summary | Query opcional owner, string, con el mismo valor por defecto que el listado. | HTTP 200, objeto con owner, total, byStatus y highPriorityOpen. | app/main.py:90; app/main.py:91; app/main.py:92; app/main.py:94; app/main.py:105 |
| POST /api/requirements | multipart/form-data con campo obligatorio file de tipo archivo. | HTTP 201, objeto con owner, fileName, storedAt y size. | app/main.py:107; app/main.py:108; app/main.py:112 |
| GET /api/backend-health | Sin cuerpo ni query declarados; usa la identidad autenticada. | HTTP 200, objeto con requestedBy, status y body. status es el codigo HTTP remoto, o 0 ante una excepcion; no es el codigo HTTP de esta ruta. | app/main.py:114; app/main.py:115; app/main.py:118; app/main.py:119; app/main.py:120; app/main.py:121 |

### Formatos

- Tarea: `id` entero; `title`, `description`, `status`, `owner`, `priority` y
  `createdAt` strings. `createdAt` serializa la columna `created_at`, generada
  mediante SQLite `datetime('now')` (app/main.py:56, 57, 64, 84).
- Creacion: valores por defecto `title=""`, `description=""`, `status="TODO"`,
  `priority="MEDIUM"` y `owner=username` del token. No se declaran enums ni
  limites de longitud; las propiedades extra no se utilizan (app/main.py:78,
  79, 80, 81, 82, 83, 84).
- Resumen: `owner` string; `total` entero; `byStatus` objeto que asigna a cada
  estado encontrado su conteo; `highPriorityOpen` cuenta tareas con prioridad
  `HIGH` y estado distinto de `DONE` y `ARCHIVED`. Sin tareas, los conteos son
  cero y `byStatus` es `{}` (app/main.py:94, 95, 97, 101, 102, 103, 104).
- Carga: `owner` es username del token, `fileName` reproduce el nombre recibido,
  `storedAt` es la ruta convertida a string y `size` es la cantidad de bytes
  leidos. La ruta no necesariamente es absoluta (app/main.py:109, 112).
- Health: `requestedBy` es username del token; `status` es entero y `body` es
  el cuerpo remoto decodificado como UTF-8 o el texto de la excepcion
  (app/main.py:119, 121).

## Flujo del token

1. Cada una de las cinco rutas inyecta `legacy_identity` con `Depends`.
2. El header Authorization tiene valor por defecto vacio. Se elimina la
   subcadena `Bearer ` mediante replace, se decodifica Base64/UTF-8 y se
   separa el resultado por el caracter `|` (app/main.py:17, 19, 20, 21).
3. La representacion esperada tiene cuatro partes: username, role, expiracion
   como entero en segundos Unix y secreto. Se comprueban cantidad de partes,
   igualdad del secreto y que la expiracion no sea menor que la hora actual
   en segundos enteros. La igualdad temporal se acepta (app/main.py:22).
4. Se retorna un dict con username y role. No hay comprobacion de firma,
   emisor o audiencia en esta funcion, ni controles de rol en las rutas
   (app/main.py:24, 68, 78, 91, 108, 115).
5. Cualquier excepcion en esa funcion se traduce a HTTP 401 e incluye su texto
   en detail (app/main.py:25, 26). Esta API consume el token; no lo emite.

## Acceso a SQLite

- `create_app` elige el archivo por argumento db_path, despues por
  WORKSHOP_DB_PATH y finalmente por `./data/workshop.db`. Crea el directorio
  padre y abre una conexion con `check_same_thread=False`, compartida por las
  rutas de esa instancia y disponible en app.state.connection
  (app/main.py:29, 30, 32, 35, 36, 46).
- Crea tasks con id autoincremental y las columnas title, description, status,
  owner, priority y created_at, todas no nulas. Si esta vacia, inserta tres
  tareas iniciales: dos de student y una de trainer; confirma la transaccion
  (app/main.py:37, 38, 39, 40, 41, 42, 43).
- Listado y resumen ejecutan SELECT filtrado por owner. Creacion ejecuta
  INSERT, commit y SELECT por el ultimo id insertado; as_task convierte la
  fila SQLite al formato publico (app/main.py:56, 70, 71, 84, 85, 86, 87, 88,
  93). No hay rollback explicito ni bloqueo por peticion en estas rutas.
- El evento shutdown cierra esa conexion. `app = create_app()` inicializa la
  instancia al importar el modulo (app/main.py:123, 125, 130).

## Carga de archivos y llamada al backend

- El directorio de archivos se elige por argumento upload_dir, despues por
  WORKSHOP_UPLOAD_DIR y finalmente por `./uploads`; se crea al inicializar
  (app/main.py:31, 33, 47).
- La carga combina ese directorio con file.filename, lee todos los bytes y
  escribe mediante Path.write_bytes. No hay validacion propia de nombre,
  extension o tamano ni registro de la carga en SQLite. Una ruta existente
  se sobrescribe si los permisos del proceso lo permiten
  (app/main.py:109, 110, 111, 112).
- Health hace GET a AUTH_HEALTH_URL o `http://localhost:8080/q/health` usando
  urllib3.PoolManager con timeout=3.0. No reenvia el token al backend; lo usa
  localmente para requestedBy (app/main.py:115, 116, 118, 119).

## Cobertura observada

Las pruebas existentes cubren listado inicial, creacion y resumen, carga de
un archivo e invalidacion de un token. No caracterizan owner ajeno, SQL con
comillas, limites de carga ni backend-health (tests/test_api.py:19, 27, 41,
54). Este documento se obtiene por lectura estatica; no afirma que esas
pruebas se hayan ejecutado en esta revision.