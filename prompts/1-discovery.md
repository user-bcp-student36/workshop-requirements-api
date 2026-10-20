# Prompt 01 — Discovery API

```text
AMBITO
Trabaja unicamente en la carpeta workshop-requirements-api/ de reqflow-workspace.
Todas las rutas de este prompt son relativas a esa carpeta. No leas ni
modifiques los otros repositorios del workspace.

CONTEXTO
API FastAPI de tareas y requerimientos (app/main.py: legacy_identity, create_app,
list_tasks, create_task, summary, upload_requirement, backend_health). Lee
primero README.md (como correrla), RETO.md (tabla de hallazgos esperados),
REGLAS.md (reglas del laboratorio) y docs/ENDPOINTS.md si existe (si no,
genéralo a partir del codigo). NO EDITES CODIGO todavia.

OBJETIVO
Mapear rutas, flujo del token, acceso a SQLite y carga de archivos, y generar
HALLAZGOS.md: una matriz de seguimiento con cada hallazgo de RETO.md que exista
realmente en el codigo, con evidencia archivo + linea.

RESTRICCIONES
No modifiques ningun archivo de codigo. No des por cierto un hallazgo que no
puedas senalar en el codigo con archivo y linea. Respeta los contratos de
docs/ENDPOINTS.md: no propongas cambiarlos, solo corregirlos por dentro.

CRITERIOS DE ACEPTACION
Cada hallazgo de RETO.md queda en HALLAZGOS.md como una fila con: id (H-01, H-02...), hallazgo,
tipo (Vulnerabilidad / Bug / Refactor / Sugerencia — el que mejor describa el
hallazgo), explicacion breve del riesgo (que puede salir mal y por que),
evidencia (archivo:linea), severidad (alta/media/baja) y estado inicial
"Pendiente". Los hallazgos quedan ordenados de mayor a menor severidad. Si un
hallazgo de RETO.md no aparece en el codigo, se marca como "No encontrado".

FORMATO DE RESPUESTA
El archivo HALLAZGOS.md, con esta tabla:
id | hallazgo | tipo | explicacion | evidencia (archivo:linea) | severidad | estado
Sin tocar codigo todavia. HALLAZGOS.md es el unico lugar donde se lleva el
seguimiento: 2-refactor.md lo va a ir actualizando hallazgo por hallazgo.
```
