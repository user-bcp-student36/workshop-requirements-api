# Plan de correccion - API FastAPI

## Alcance y seleccion

Se proponen H-02 (SQL), H-03 (archivos) y H-04 (autorizacion), los tres de
severidad alta abordables dentro de este repositorio. Todos figuran como
Pendiente en HALLAZGOS.md. Este documento no registra estados ni los cambia:
HALLAZGOS.md sigue siendo el unico seguimiento. Esta entrega solo crea PLAN.md;
no implementa cambios ni escribe o ejecuta las pruebas propuestas.

H-01 tambien es alta, pero el token documentado no tiene firma verificable.
Validar un JWT real exige un acuerdo con el emisor sobre formato firmado,
algoritmo permitido, claves, emisor y audiencia. No es posible garantizarlo
aceptando a la vez cualquier token Base64 legacy, y no se propone un fallback
inseguro. Se deja fuera de esta tanda, sin leer ni modificar otros repositorios.
H-05, H-06 y H-07 tampoco se resuelven completos en esta tanda; las pequenas
extracciones y modelos siguientes solo apoyan los tres cambios seleccionados.

## Contrato y condiciones previas

- Mantener intacto docs/ENDPOINTS.md, las cinco rutas, metodos, header
  Authorization, query owner, JSON de tareas y multipart con campo file.
- Conservar respuestas correctas 200/201, nombres y tipos de campos,
  createdAt, orden por id, valores por defecto y reglas del resumen.
  Mantener create_app(db_path, upload_dir), configuracion de directorios,
  inicializacion de tareas y cierre de SQLite. No tocar backend-health.
- Preservar el comportamiento de entradas legitimas y autorizadas. No
  convertir inyeccion, acceso ajeno o escritura fuera del directorio en
  requisitos que los tests deban mantener despues de la correccion.
- Hay limites reales: el documento describe owner ajeno aceptado, nombres de
  archivo sin restricciones y sobrescritura. Corregirlos cambia necesariamente
  la aceptacion de esas entradas. Antes de implementar, confirmar que esas
  descripciones son evidencia del legado, no garantias de compatibilidad.
  Si se exige preservarlas literalmente, H-03 y H-04 no pueden resolverse bajo
  esa restriccion; detener esos cambios y pedir aclaracion, sin editar el contrato.
- No inventar una politica de extensiones o tamano. Acordar sus valores antes
  de implementar H-03, conservando el caso valido requirements.txt de las
  pruebas. El contrato tampoco define errores para archivos o autorizacion:
  cualquier codigo nuevo debe acordarse antes, no introducirse silenciosamente.
- Usar un objeto de error con detail y texto generico, sin excepciones crudas.
  Los codigos de rechazo mencionados abajo son propuestas sujetas a ese acuerdo,
  no contratos nuevos aprobados.
- No agregar dependencias: SQLite, pathlib, tempfile y las primitivas de
  archivos de la biblioteca estandar son suficientes. Pydantic, FastAPI,
  pytest y pytest-cov ya son parte del proyecto.

## H-02 - SQL: filtros e inserts concatenados

### Problema

list_tasks concatena owner en SELECT (app/main.py:69, 70); create_task concatena
campos del cuerpo en INSERT (app/main.py:79, 84) y el id en el SELECT posterior
(app/main.py:87); summary concatena owner (app/main.py:92, 93). Las entradas
pueden modificar la sentencia y las comillas legitimas pueden causar errores.

### Cambio propuesto

- Extraer el acceso de tareas a un repositorio: listar por propietario,
  insertar tarea, recuperar por id y obtener filas para el resumen. Cada
  operacion usa placeholders ? y parametros separados, incluido el id.
  Conservar esquema, datetime('now'), transaccion y orden actuales.
- Mantener SQL constante con nombres explicativos. La insercion confirma la
  transaccion solo al completarse y hace rollback ante un error de SQLite;
  no devolver el texto interno de esa excepcion.
- Extraer servicio para coordinar la creacion y el resumen; las rutas solo
  reciben entradas, invocan servicio y devuelven modelos de respuesta.
- Introducir modelos Pydantic de entrada y respuesta con los campos actuales,
  alias createdAt y defaults nombrados. Un normalizador previo conserva la
  conversion str de campos presentes, incluidos numeros, booleanos y null;
  aplica defaults solo a campos ausentes e ignora extras como hoy. No imponer
  enums, campos obligatorios adicionales ni limites de longitud nuevos.
- El repositorio recibe el propietario resuelto por el servicio de H-04,
  no la query ni el cuerpo sin autorizar. Parametrizacion y autorizacion
  son controles distintos y deben probarse por separado.

### Archivos a tocar durante la implementacion

- app/main.py: conectar las rutas de tareas y resumen con el servicio.
- app/task_repository.py (nuevo): concentrar las operaciones SQLite de tareas.
- app/task_service.py (nuevo): creacion, autorizacion y calculo del resumen.
- app/models.py (nuevo): modelos compartidos de entrada y salida.
- tests/test_api.py: ampliar las pruebas existentes, sin otra suite paralela.

### Pruebas de caracterizacion antes de tocar produccion

Ampliar tests/test_api.py usando create_app, tmp_path, headers y TestClient:
verificar lista inicial completa ordenada por id, tipos y claves de cada tarea;
creacion con {} y con campos presentes de distintos tipos; defaults, extras
ignorados y formato createdAt. Crear estados DONE, ARCHIVED y abiertos para
comprobar exactamente total, byStatus y highPriorityOpen. Cubrir el resumen
vacio y persistencia al volver a abrir la misma DB.

Estas pruebas de compatibilidad deben pasar en el legado antes de extraerlo.
Agregar por separado regresiones inicialmente fallidas: titulo y descripcion
con apostrofos se guardan literalmente; un usuario con apostrofo en su nombre
puede crear y consultar sus propias tareas; cadenas con metacaracteres SQL
no amplian resultados ni alteran filas ajenas. Probar parametros del
repositorio con la conexion SQLite temporal real, sin depender de que H-04
bloquee antes la entrada. No mantener una prueba que exija conservar inyeccion.

## H-03 - Files: nombre recibido sin limites de extension o tamano

### Problema

upload_requirement combina el directorio con file.filename, lee todos los
bytes y escribe directamente (app/main.py:108, 109, 110, 111). No valida
contencion, extension, tamano ni colisiones; puede salir del directorio,
sobrescribir archivos y consumir memoria sin un limite propio.

### Cambio propuesto

- Extraer un servicio de cargas que valide metadatos y coordine almacenamiento.
  La ruta conserva file, identidad y respuesta owner/fileName/storedAt/size;
  fileName sigue siendo el nombre recibido y storedAt la ruta realmente usada.
  Para nombres simples admitidos, mantener su nombre y representacion de ruta.
- Normalizar y validar un unico componente de nombre, contemplando las
  convenciones Windows y POSIX: rechazar rutas absolutas, unidades, separadores,
  componentes de traversal, nombres vacios y nombres especiales del sistema.
  Comprobar que el destino resuelto pertenece al directorio configurado.
  No aceptar un nombre peligroso simplemente porque basename lo recorta.
- Validar la extension normalizada contra una lista permitida acordada y
  contar bytes reales mientras se lee por bloques; no confiar en Content-Length
  ni en el MIME declarado. Usar constantes/configuracion con nombres para
  UPLOAD_ALLOWED_EXTENSIONS, UPLOAD_MAX_BYTES y UPLOAD_CHUNK_BYTES, cuyos valores
  deben acordarse o justificarse antes de implementarse.
- Almacenar en un directorio controlado por la aplicacion, sin permisos de
  escritura de terceros. Usar un temporal interno y publicacion exclusiva
  que no sobrescriba un destino existente ni siga un enlace de destino.
  Limpiar temporales y archivos parciales ante exceso de tamano o fallo.
  Comprobar el comportamiento tanto en Windows como en POSIX; no asumir que
  una comprobacion exists seguida de write_bytes evita carreras.
- Reutilizar las primitivas estandar y separar validacion de nombre, lectura
  limitada y publicacion. Capturar errores especificos y usar retorno temprano.
  Proponer, sujeto al acuerdo de errores, 400 para nombre invalido, 413 para
  exceso de tamano, 415 para extension no admitida y 409 para colision.

### Archivos a tocar durante la implementacion

- app/main.py: delegar la ruta de carga sin cambiar su firma publica.
- app/upload_service.py (nuevo): validacion y coordinacion de la carga.
- app/upload_storage.py (nuevo): escritura limitada y publicacion segura.
- app/models.py: modelo de la respuesta de carga con las mismas claves.
- tests/test_api.py: ampliar caracterizacion y regresiones de archivos.

### Pruebas de caracterizacion antes de tocar produccion

Extender el test existente de requirements.txt para comprobar HTTP 201,
claves y tipos exactos, identidad del owner, fileName original, storedAt
esperado segun el directorio configurado, size y bytes escritos. Caracterizar
un archivo vacio y ausencia del campo file (422); mantener el caso vacio si
la politica acordada no lo prohibe. Probar falta de autenticacion (401).

Escribir antes del cambio regresiones de seguridad, separadas de las anteriores:
nombres absolutos, separadores Windows/POSIX, componentes ascendentes y
destinos con enlace no escriben fuera del directorio; extension no admitida
no crea archivo; limite exacto se acepta y limite mas un byte se rechaza,
contando bytes incluso sin Content-Length. Dos cargas al mismo destino no
sobrescriben el primero. Simular fallo de escritura y verificar limpieza.
Usar solo tmp_path, datos sinteticos y los limites acordados; no ejecutar
pruebas destructivas sobre uploads real. Las regresiones deben fallar en
el legado y pasar con la correccion, con codigos acordados previamente.

## H-04 - Autorizacion: el cliente elige otro owner

### Problema

list_tasks y summary prefieren owner recibido a username (app/main.py:68, 69,
91, 92); create_task admite un owner del JSON (app/main.py:83). No hay
comparacion con identidad ni autorizacion por rol. H-01 permite ademas
falsificar esa identidad: corregir H-04 no elimina ese riesgo residual.

### Cambio propuesto

- Mantener owner en query y JSON para compatibilidad del esquema. Centralizar
  en el servicio una funcion que compare el propietario solicitado con la
  identidad y devuelva siempre identity.username para acceder al repositorio.
- Listado y resumen: owner ausente o vacio conserva el fallback actual; un
  owner igual a la identidad es valido; uno distinto se rechaza antes del SQL.
  Creacion: owner ausente usa la identidad; si esta presente, normalizarlo
  como hoy y exigir coincidencia, sin atribuir silenciosamente una tarea ajena.
- Proponer HTTP 403 con detail generico para una identidad autenticada que
  solicita otro propietario, sujeto al acuerdo de compatibilidad anterior.
  No inventar privilegios de TRAINER/ADMIN: ninguna excepcion por rol esta
  definida en las convenciones consultadas.
- Reutilizar la misma politica para las tres rutas, con retornos tempranos.
  El repositorio nunca toma el owner del cliente como autoridad. Conservar
  el verificador legacy por ahora; declarar H-01 como riesgo abierto y no
  afirmar que la identidad es criptograficamente confiable tras esta tanda.

### Archivos a tocar durante la implementacion

- app/main.py: pasar identidad y solicitud al servicio de tareas.
- app/task_service.py: unica politica de propietario y coordinacion.
- app/models.py: identidad tipada interna y entradas compatibles.
- tests/test_api.py: caracterizacion y regresiones de aislamiento de usuarios.

### Pruebas de caracterizacion antes de tocar produccion

Con los helpers existentes, comprobar listado y resumen sin owner, con query
vacia y con owner propio; verificar owner en el resumen y creacion con owner
ausente o propio. Verificar que student y trainer ven sus tareas cuando cada
uno usa su identidad, y que el token invalido sigue dando 401. Ejecutar esas
pruebas de compatibilidad antes de mover codigo.

Agregar regresiones de seguridad inicialmente fallidas: student no puede
listar ni resumir trainer ni crear una tarea a su nombre; tampoco trainer
puede acceder a student solo por su rol. Confirmar el rechazo acordado y que
no se insertan filas. En pruebas unitarias de la politica, comprobar que las
operaciones rechazadas no llaman al repositorio. Esas pruebas demuestran
autorizacion respecto de la identidad recibida, no resistencia a token falsificado.

## Secuencia y criterios de verificacion

1. Resolver los acuerdos de compatibilidad y politica de carga anteriores.
   Sin ellos, no implementar las partes bloqueadas ni alterar contratos.
2. Escribir y ejecutar caracterizacion en tests/test_api.py sobre el legado;
   guardar una linea base verde. Escribir las regresiones de seguridad por
   separado, identificando los fallos esperados, sin noqa ni exclusiones.
3. Implementar H-02 y el control H-04 juntos en el recorrido ruta -> servicio
   -> repositorio; asi no se presenta SQL seguro como autorizacion resuelta.
   Implementar H-03 despues usando los mismos modelos de respuesta.
4. Mantener una responsabilidad por funcion, nombres explicativos, modelos
   compartidos y una sola politica de owner. Extraer conversion de filas y
   agregacion, combinar condiciones HIGH/no DONE/no ARCHIVED y nombrar defaults,
   SQL, limites y mensajes; no hacer una limpieza general del monolito.
5. Ejecutar desde la raiz de este repositorio
   `python -m pytest tests/test_api.py` tras cada cambio. Como puerta final,
   `python -m pytest tests/test_api.py --cov=app --cov-branch --cov-report=term-missing`;
   verificar cobertura de al menos 85% del codigo modificado, incluidas ramas
   de rechazo y limpieza. El total de app no sustituye la revision de las
   lineas modificadas. Usar el entorno del proyecto; no instalar dependencias nuevas.
6. Comparar el esquema OpenAPI y las respuestas autorizadas con la linea base:
   mismas rutas, parametros, campos y estados correctos. Revisar el diff para
   confirmar docs/ENDPOINTS.md intacto y ningun cambio fuera de este repositorio.
   Actualizar exclusivamente HALLAZGOS.md hallazgo por hallazgo cuando exista
   evidencia de correccion y sus pruebas pasen; PLAN.md no actua como tablero.