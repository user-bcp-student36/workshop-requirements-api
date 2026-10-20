# PR coordinado: Issue #1 - Token firmado entre emisor y consumidor

## Objetivo

Corregir el hallazgo aprobado de identidad, rol y expiracion falsificables.
Este es un expediente local para PRs coordinados en los tres repos, no un PR
publicado ni una declaracion de cierre. Rama observada: `target_day02`.
La rama base de publicacion y los SHA de los commits quedan por confirmar.

## Que cambio y por que

- Java conecta AuthService con TokenService y retira LegacyTokenUtil. Usa JWT
  RS256 y exige clave externa RSA de al menos 2048 bits, emisor y audiencia.
- FastAPI usa PyJWT 2.15.1 con soporte criptografico para verificar la firma,
  `iss`, `aud`, `sub`, un unico rol en `groups` y `exp` entero. Rechaza cuando
  ahora >= exp, sin tolerancia. No hay fallback legacy.
- La clave publica se carga al crear la app; configuracion ausente o invalida
  no permite acceso. El consumidor nunca recibe material privado de firma.
- Angular no cambia codigo productivo: agrega una prueba de persistencia y
  envio como Bearer del JWT real obtenido del login HTTP Java.
- Las decisiones anteriores y el nuevo login tras el corte fueron confirmados
  expresamente por el usuario durante esta implementacion.

## Que se preservo

- POST /auth/login: entradas, codigos, mensajes y estructura con token,
  expiresIn, user y debug; duracion 3600 y escape de displayName conservados.
- Identidad y rol del usuario autenticado; encabezado Bearer y operaciones
  de tareas, resumen, cargas y backend-health. Sin privilegios nuevos por rol.
- Diferencias autorizadas: representacion del token, rechazo legacy y limite
  temporal estricto. Los errores nuevos de validacion usan un detalle generico
  dentro de la estructura 401 existente, sin exponer el error criptografico.
- docs/ENDPOINTS.md permanece intacto por la restriccion del plan previo;
  sus descripciones legacy del token son historicas y no describen este cambio.
  El presente expediente y los README documentan el contrato aprobado del token.

## Como se probo

Ejecuciones locales del 2026-10-09, JDK 21 y Python 3.13.16:

| Comprobacion | Comando / evidencia | Resultado |
|---|---|---|
| Baseline Java | mvn -f workshop-auth-backend-template/pom.xml -Dquarkus.http.test-port=0 test -q | 31 pruebas aprobadas antes del cambio |
| Baseline Python | .venv/Scripts/python.exe -m pytest, desde la API | 98 aprobadas, 1 symlink omitido |
| Emisor enfocado | mvn -f workshop-auth-backend-template/pom.xml -Dtest=TokenServiceTest test -q | 3 aprobadas |
| Gate Java final | mvn -f workshop-auth-backend-template/pom.xml -Dquarkus.http.test-port=0 verify -q, con entorno interop habilitado | 31 unitarias/HTTP y 4 IT aprobadas; interop no omitida |
| Gate Python final | .venv/Scripts/python.exe -m pytest --cov=app --cov-report=term-missing --cov-report=xml:coverage.xml | 181 aprobadas, 1 symlink omitido; 99% conjunto |
| Gate Angular | npm --prefix workshop-login-frontend-template test, con fixture real temporal | 75 aprobadas, incluida la prueba JWT real |
| Cobertura Java | target/site/jacoco/jacoco.xml | AuthService y TokenService: 100% lineas y ramas |
| Cobertura consumidor | coverage.xml | auth_token y main: 100% lineas y ramas |
| SCA nuevas dependencias | POST https://api.osv.dev/v1/query para versiones exactas | Sin advisories devueltos para PyJWT 2.15.1, cryptography 50.0.2, cffi 2.1.1 y pycparser 3.1 |

El baseline Java inicial fallo por el puerto 8081 ocupado; se repitio con puerto
dinamico sin detener procesos ajenos. La primera suite Python completa detecto
una colision del fixture de clave con directorios inspeccionados por cargas;
se corrigio el aislamiento y se repitio el gate completo hasta el resultado
anterior. No se cambiaron las expectativas de almacenamiento para ocultarla.

### Trazabilidad a la spec

- CA-1: AuthResourceTest.issuedLoginTokensAuthenticateInPythonConsumer obtiene
  tokens mediante POST /auth/login y los verifica en FastAPI para ambos usuarios.
- CA-2/3/4: test_jwt_rejects_untrusted_claims_before_operations prueba alteracion
  de identidad/rol/expiracion, otra clave, sin firma, HS256, emisor/audiencia
  incorrectos y claims requeridos ausentes en las cinco operaciones protegidas;
  comprueba ausencia de escrituras y de llamada al backend ante rechazo.
- CA-5: test_endpoint_token_expiry_equality y
  test_jwt_preserves_identity_role_and_strict_expiration usan reloj controlado.
- CA-6: test_endpoint_authentication_errors rechaza fixtures legacy;
  TokenServiceTest inspecciona claims sin imprimirlos. El emisor legacy y
  su constante fueron eliminados del codigo productivo.
- CA-7: AuthResourceTest, AuthFrameworkIT, las caracterizaciones FastAPI y
  las suites Angular conservan contratos salvo los cambios autorizados.

### Repetir interoperabilidad desde la raiz del workspace

```powershell
$env:REQFLOW_TEST_PYTHON = (Resolve-Path workshop-requirements-api-template/.venv/Scripts/python.exe).Path
$env:REQFLOW_TEST_API_ROOT = (Resolve-Path workshop-requirements-api-template).Path
$env:REQFLOW_TEST_LOGIN_FIXTURE = Join-Path ([System.IO.Path]::GetTempPath()) ('reqflow-login-' + [guid]::NewGuid().ToString() + '.json')
try {
    mvn -f workshop-auth-backend-template/pom.xml '-Dquarkus.http.test-port=0' verify -q
    if ($LASTEXITCODE -ne 0) { throw 'Java gate failed' }
    npm --prefix workshop-login-frontend-template test
    if ($LASTEXITCODE -ne 0) { throw 'Angular gate failed' }
} finally {
    Remove-Item -LiteralPath $env:REQFLOW_TEST_LOGIN_FIXTURE -ErrorAction SilentlyContinue
    Remove-Item Env:REQFLOW_TEST_LOGIN_FIXTURE, Env:REQFLOW_TEST_PYTHON, Env:REQFLOW_TEST_API_ROOT -ErrorAction SilentlyContinue
}
```

Las claves RSA se generan para las pruebas; la privada se elimina al terminar
el recurso Quarkus. El intercambio Java/Python va por stdin. El fixture de login
es temporal y no debe adjuntarse ni versionarse. La prueba Angular usa HTTP
simulado con ese JWT real, no demuestra un flujo de navegador end-to-end.
En CI de repos individuales la prueba entre repos se omite si no se proporciona
el entorno; publicar la evidencia coordinada antes del merge.

## Que no se resolvio

- CORS, mantenimiento WAL, exposicion de errores Java, advisories preexistentes,
  limites multipart antes del spool y restantes hallazgos quedan fuera.
- CodeQL, Dependency Review y revisiones Cyber/QE/LT remotas siguen pendientes;
  la consulta OSV no es una auditoria completa ni certifica ausencia de CVEs.
- La omision de symlink responde a capacidad de Windows, no a un cierre del
  riesgo de almacenamiento. No se modificaron ni desactivaron workflows.
- Los cambios previos de HU-01.md y Skills no pertenecen a este PR y no se
  revirtieron ni se deben incluir automaticamente al preparar los commits.
- No se crearon commits, branches, issues ni PRs remotos; este documento prepara
  el contenido y evidencia para publicacion revisada en cada repositorio.

## Activacion y como revertir

Configurar en Java AUTH_TOKEN_KEY_LOCATION, AUTH_TOKEN_ISSUER y
AUTH_TOKEN_AUDIENCE; en FastAPI AUTH_TOKEN_PUBLIC_KEY_LOCATION y los mismos
emisor/audiencia. Distribuir solo la publica al consumidor. Coordinar el corte
y solicitar nuevo login; las sesiones legacy dejan de autenticar.

Una reversion de commits debe coordinarse entre repos, sin reactivar acceso
legacy como recuperacion automatica. Ante incompatibilidad, detener el acceso
afectado y recuperar una version firmada compatible validada. La reversion
operativa que comprometa esa garantia requiere una decision humana explicita.

## Validaciones por rol y gates

- [x] Developer: compilacion, suites y cobertura locales ejecutadas.
- [x] QE: casos positivos, negativos y regresion documentados; revision QE pendiente.
- [ ] Cyber: revision de SAST, dependencias, configuracion y material de confianza.
- [ ] Lider tecnico: confirmar diseno, diff, coordinacion y rama base.
- [ ] Aprobador LT: confirmar checks remotos y evidencia antes de merge.
- [x] Cobertura >=85% del codigo productivo modificado.
- [x] Sin valores de tokens, secretos ni credenciales en este expediente.
- [ ] Confirmar gates remotos, politica de despliegue y cierre humano de hallazgos.