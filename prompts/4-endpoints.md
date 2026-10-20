# Prompt 04 — Actualizar el contrato (docs/ENDPOINTS.md)

Corre esto cuando `HALLAZGOS.md` no tenga hallazgos "Pendiente".

```text
AMBITO
Trabaja unicamente en la carpeta workshop-requirements-api/ de reqflow-workspace.
Todas las rutas de este prompt son relativas a esa carpeta. No leas ni
modifiques los otros repositorios del workspace.

CONTEXTO
API FastAPI ya refactorizada. docs/ENDPOINTS.md tiene el contrato legacy
(defectos incluidos); hay que actualizarlo a como quedo el codigo hoy. Consulta
el codigo y los documentos del repositorio que consideres necesarios para
verificar cada campo. NO EDITES CODIGO, esto es solo documentacion.

OBJETIVO
Actualizar docs/ENDPOINTS.md para que un desarrollador que nunca vio esta API
pueda integrar contra ella sin leer el codigo fuente.

RESTRICCIONES
No inventes campos, tipos o codigos de respuesta que no existan en el codigo. Si
algo no esta claro leyendo el codigo, márcalo como pregunta abierta. No
documentes cada endpoint con una sola linea: sigue la estructura de abajo
completa.

CRITERIOS DE ACEPTACION
Por cada endpoint (GET/POST /api/tasks, GET /api/summary, POST /api/requirements,
GET /api/backend-health), docs/ENDPOINTS.md incluye TODO lo siguiente (nada es
opcional):
1. Que hace (una frase, en terminos de negocio).
2. Si requiere autenticacion y que header exacto.
3. Request: tabla campo/parametro | tipo | obligatorio | descripcion, mas un
   ejemplo real y completo.
4. Response exitosa: codigo de estado, tabla campo | tipo | descripcion, mas un
   ejemplo real y completo.
5. Cada respuesta de error posible: codigo de estado, cuando ocurre, y un
   ejemplo de cuerpo de esa respuesta.
6. Notas de seguridad relevantes (por ejemplo, que la autorizacion ahora
   depende de la identidad del token y no de un parametro `owner`).
Cada campo y cada ejemplo tienen que poder verificarse contra el codigo real.

FORMATO DE RESPUESTA
El archivo docs/ENDPOINTS.md actualizado, siguiendo exactamente esa estructura
de 6 puntos por endpoint. Al final, que documentos consultaste.
```
