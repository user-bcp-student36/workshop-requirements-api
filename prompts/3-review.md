# Prompt 03 — Review API

```text
AMBITO
Trabaja unicamente en la carpeta workshop-requirements-api/ de reqflow-workspace.
Todas las rutas de este prompt son relativas a esa carpeta. No leas ni
modifiques los otros repositorios del workspace.

CONTEXTO
El PR implementa uno o mas hallazgos de HALLAZGOS.md. Consulta los documentos
del repositorio que consideres necesarios para justificar cada observacion (por
ejemplo README.md, RETO.md, docs/ENDPOINTS.md, docs/GOOD_PRACTICES.md,
REGLAS.md) y al final dime cuales usaste.

OBJETIVO
Revisar el PR verificando que cada hallazgo marcado "Resuelto" en HALLAZGOS.md
este realmente corregido, buscando especificamente: SQL injection, IDOR (un
usuario consultando datos de otro owner), validacion incompleta del token, path
traversal en la carga de archivos, consumo de memoria innecesario, excepciones
verbosas, dependencias vulnerables, falta de tipos, duplicacion y pruebas
insuficientes.

RESTRICCIONES
No apruebes un PR que reduzca quality gates o que marque un hallazgo como
"Resuelto" sin corregirlo de verdad. No inventes riesgos que no puedas senalar
con archivo y linea.

CRITERIOS DE ACEPTACION
Cada hallazgo "Resuelto" de HALLAZGOS.md queda verificado con evidencia, o se
regresa a "Pendiente" si el PR no lo corrigio del todo. Se exige evidencia
concreta para cada observacion.

FORMATO DE RESPUESTA
Observaciones clasificadas en bloqueantes, importantes y sugerencias. Para cada
bloqueante: por que bloquea el merge y que evidencia lo respalda. Si algun
hallazgo vuelve a "Pendiente", dilo explicitamente. Al final, que documentos
consultaste.
```

Si encontraste algo que no estaba en `HALLAZGOS.md` (un bug nuevo, una
sugerencia importante), agrégalo ahí mismo como una fila nueva con estado
"Pendiente" — no lo dejes solo mencionado en el chat. Se resuelve después con
[resolver-item.md](resolver-item.md), igual que cualquier otro item.
