# Prompt 05 — Documentar y completar las pruebas (docs/TESTING.md)

Corre esto despues de 4-endpoints.md.

```text
AMBITO
Trabaja unicamente en la carpeta workshop-requirements-api/ de reqflow-workspace.
Todas las rutas de este prompt son relativas a esa carpeta. No leas ni
modifiques los otros repositorios del workspace.

CONTEXTO
API FastAPI ya refactorizada. docs/ENDPOINTS.md ya refleja el contrato real y
detallado. Consulta ese archivo, REGLAS.md (meta de cobertura) y cualquier otro
documento que consideres necesario.

OBJETIVO
Generar docs/TESTING.md y completar las pruebas que falten para cada endpoint de
docs/ENDPOINTS.md, cubriendo tres categorias: camino feliz, casos borde y
errores.

RESTRICCIONES
No inventes endpoints ni comportamientos que no esten en docs/ENDPOINTS.md. No
adaptes un test para que pase con un bug existente: si encuentras un bug,
repórtalo aparte, no lo escondas dentro del test.

CRITERIOS DE ACEPTACION
Por cada endpoint de docs/ENDPOINTS.md hay al menos: un test de camino feliz
(dato valido), un test de caso borde (payload vacio, archivo sin extension,
limite de tamano), y un test por cada respuesta de error documentada (incluido
un test que confirma que un usuario no puede leer tareas de otro owner).
Cobertura del codigo modificado en 85% o superior.

FORMATO DE RESPUESTA
El archivo docs/TESTING.md con una tabla (endpoint | caso | tipo | resultado
esperado) y despues el codigo de los tests, corriendo en verde. Al final, que
documentos consultaste.
```
