# Hallazgos - API FastAPI

Matriz de seguimiento de los siete casos de `RETO.md`, contrastados
con el codigo y las pruebas indicadas. Solo este archivo registra estados; el
refactor debe actualizar cada fila sin cambiar los contratos de
`docs/ENDPOINTS.md`.

| id | hallazgo | tipo | explicacion | evidencia (archivo:linea) | severidad | estado |
|---|---|---|---|---|---|---|
| H-01 | Auth: token Base64 con secreto embebido | Vulnerabilidad | Base64 solo codifica. El secreto literal permite construir identidades y roles arbitrarios; no se verifica firma, emisor ni audiencia. La expiracion SI se compara con la hora actual, pero tambien procede de contenido sin firma. | app/main.py:21; app/main.py:27; app/main.py:28; app/main.py:29; app/main.py:30; app/main.py:32 | alta | Pendiente |
| H-02 | SQL: filtros e inserts concatenados | Vulnerabilidad | Riesgo original: datos del cliente alteraban SQL o fallaban con comillas. Resolucion: repositorio con placeholders y parametros separados, transaccion con rollback, modelos compatibles y errores genericos. Caracterizacion verde antes (26 tests) y despues (34); cobertura conjunta de modelos/repositorio/servicio 96%. | app/task_repository.py:10; app/task_repository.py:11; app/task_repository.py:12; app/task_repository.py:13; app/task_repository.py:36; tests/test_api.py:203; tests/test_api.py:250 | alta | Resuelto |
| H-03 | Files: uso directo de upload.filename sin limites de extension o tamano | Vulnerabilidad | Reabierto en revision: nombre, extension, contencion y publicacion exclusiva estan corregidos, pero el limite de 5 MiB se aplica despues de que FastAPI parsea multipart. Probe con UploadFile.write instrumentado: 6 MiB completos fueron procesados y enviados al spool antes del 413 e incluso antes del 401 sin token; un archivo adicional no usado de 6 MiB produjo 201. Falta limitar bytes recibidos y partes antes/durante el parseo, sin confiar solo en Content-Length, y probar rechazo temprano. La lectura de 64 KiB solo limita la copia posterior; el directorio debe seguir bajo control exclusivo de la aplicacion. | app/main.py:87; app/main.py:88; app/upload_service.py:53; app/upload_service.py:54; app/upload_storage.py:22; app/upload_storage.py:24; tests/test_api.py:314; tests/test_api.py:322 | alta | Pendiente |
| H-04 | Autorizacion: el cliente puede consultar otro owner | Vulnerabilidad | Riesgo original: consultas y altas aceptaban owner ajeno. Resolucion: una politica compartida compara con la identidad y rechaza con 403 antes del repositorio, sin privilegios inventados por rol. Caracterizacion verde antes (26 tests) y despues (34); servicio al 100% de cobertura. H-01 sigue permitiendo falsificar la identidad legacy y no se considera resuelto. | app/task_service.py:14; app/task_service.py:25; app/task_service.py:29; app/task_service.py:33; tests/test_api.py:220; tests/test_api.py:231 | alta | Resuelto |
| H-05 | SCA: urllib3 2.5.0 y python-multipart 0.0.21 fijados | Vulnerabilidad | Revision OSV: python-multipart 0.0.21 esta afectado por CVE-2026-53539 (parseo URL-encoded cuadratico; corregido para ese advisory en 0.0.30). Probe de seis bytes confirma QuerystringParser.write antes del 401 en la ruta de cargas; no se ejecuta un ataque DoS. urllib3 2.5.0 tambien aparece afectado por CVE-2026-97689, pero ese advisory requiere stream/read_chunked y no se demuestra ese uso en backend_health. Revisar todos los advisories antes de elegir versiones corregidas; no afirmar explotabilidad por el pin solamente. | requirements.txt:4; requirements.txt:5; app/main.py:11; app/main.py:87; app/main.py:94 | alta | Pendiente |
| H-06 | Calidad: dict, excepciones amplias, condicionales y duplicacion | Refactor | Avance parcial al resolver H-02/H-03/H-04: modelos para tareas/cargas, politica de owner unica y resumen sin anidamiento. Quedan dict y except Exception con detalles crudos en autenticacion y backend-health. El refactor completo de calidad queda fuera de esta tanda; no se introducen enums que alteren el contrato. | app/main.py:25; app/main.py:33; app/main.py:34; app/main.py:91; app/main.py:96; app/main.py:97 | media | Pendiente |
| H-07 | Arquitectura: rutas, DB, reglas y serializacion en un archivo | Refactor | Avance parcial: tareas y cargas delegan en servicio/repositorio y modelos. create_app aun inicializa la DB y comparte su conexion; autenticacion y llamada HTTP siguen en main. El refactor completo y el ciclo de vida quedan fuera de esta tanda. La conexion es por instancia de app, no una variable global independiente. | app/main.py:25; app/main.py:41; app/main.py:47; app/main.py:49; app/main.py:58; app/main.py:91; app/main.py:100 | baja | Pendiente |

## Alcance de la evidencia

- Los siete casos de RETO.md tienen presencia verificable en los archivos; no
  hay un caso completo que deba marcarse como "No encontrado". La revision SCA
  ahora cuenta con advisories consultados en OSV y una prueba de alcance del
  parser; no equivale a una auditoria exhaustiva de todas las dependencias.
- Las evidencias se actualizan a las ubicaciones actuales. H-02/H-03/H-04
  cuentan con caracterizacion y regresiones ejecutadas usando datos sinteticos
  y almacenamiento temporal; no se ejecutaron ataques contra servicios reales
  ni verificaciones de advisories. El contrato documental permanece intacto.
- Antes del refactor: 26 pruebas verdes. Tras H-02/H-04: 34 verdes.
  Tras H-03: 60 verdes; con concurrencia y symlink: POSIX 62 verdes (Python
  3.14.7). Windows no permite el symlink real sin privilegios; se omite solo
  esa prueba por capacidad del sistema, no una comprobacion de seguridad.
- Cobertura de lineas y ramas de la API: 96%; modelos, servicio de tareas y
  modulos de cargas: 100%; repositorio: 89%; main: 93%, con sus 24 lineas
  ejecutables modificadas cubiertas. La llamada backend-health no se modifica.
- Politica y rechazos acordados antes de implementar: archivos .txt/.md/.pdf,
  maximo 5 MiB, vacios permitidos; 400/413/415/409 para nombre/tamano/extension/
  colision, 403 para owner ajeno. Bloques de 64 KiB limitan memoria por lectura.
  No se agregaron dependencias ni se modifico PLAN.md.
- Revision del PR (2026-10-06): H-03 vuelve a Pendiente por limite tardio de
  recepcion multipart. Las pruebas verdes y la cobertura anteriores no
  verifican rechazo antes del spool, ni partes de archivo adicionales; los
  resultados historicos no equivalen al cierre completo de ese riesgo.
- Fuentes SCA consultadas en la revision: [python-multipart, CVE-2026-53539](https://osv.dev/vulnerability/GHSA-5rvq-cxj2-64vf)
  y [urllib3, CVE-2026-97689](https://osv.dev/vulnerability/GHSA-vxq7-64xx-v4gw).
  H-05 conserva Pendiente y se reclasifica como Vulnerabilidad/alta por el
  parser URL-encoded alcanzable sin autenticacion; el advisory de urllib3
  citado no se considera una explotacion demostrada de backend-health.
- No se agregan como filas independientes asuntos ajenos a la tabla de
  RETO.md. El mapa de rutas, token, SQLite y archivos esta en
  `docs/ENDPOINTS.md`, sin duplicar alli el seguimiento.

## Discrepancia documental detectada al completar pruebas (2026-10-06)

`docs/ENDPOINTS.md` aun describe el monolito previo al refactor: afirma ausencia
de limites de archivos y de manejadores propios de almacenamiento, y no
enumera el 403 de owner. La API actual aplica la politica de H-03/H-04 y
devuelve errores genericos de almacenamiento. Esto no es un fallo nuevo de
las rutas ni se corrige cambiando expectativas de tests: el contrato publicado
necesita una actualizacion separada. Se conserva intacto en esta tarea.

`docs/TESTING.md` distingue el contrato publicado de las regresiones de
seguridad ya existentes. Las 37 pruebas nuevas pasan sin cambios de
produccion; suite completa: 98 aprobadas y un symlink omitido por permisos de
Windows. H-01 y H-03 siguen pendientes: pruebas verdes no demuestran firma
del token ni rechazo temprano del multipart antes del spool.