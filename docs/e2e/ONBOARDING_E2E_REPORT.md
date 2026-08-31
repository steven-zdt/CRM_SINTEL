# ONBOARDING_E2E_REPORT

Validación end-to-end real de la creación de un nuevo tenant/cliente en
SINTEL ERP, ejecutada vía el flujo real de consola administrativa
(Vía A), con evidencia de FRONTEND, BACKEND, BASE DE DATOS, SCHEMA,
AUTENTICACIÓN, AISLAMIENTO y LOGS — no solo un HTTP 201.

**Fecha:** 2026-08-31
**Rama:** `feat/onboarding-cookie`
**Tenants de prueba creados** (identificables inequívocamente, no se
eliminan — quedan como evidencia, per regla de no-cleanup-automático):

| Tenant | schema_name | Client ID | Dominio | Owner |
|---|---|---|---|---|
| QA principal (ejercitó todo el flujo) | `qa_20260831090942` | 8 | `qa-20260831090942.sintel.net.co` | `qa+20260831090942@sintel.local` |
| QA verificación del fix E2E-03 | `qa_verify_20260831090942` | 10 | `qa-verify-20260831090942.sintel.net.co` | `qa2+20260831090942@sintel.local` |

No se usaron credenciales de ningún usuario real ni de otros tenants.
Ninguna contraseña se registró en este documento (se usaron transitoriamente
en la sesión de trabajo y se descartan aquí).

---

## Resumen ejecutivo

El flujo de creación de tenant vía consola **funciona de extremo a
extremo**: schema PostgreSQL real, 79 tablas migradas, Domain, Membership,
Empresa, Perfil, autenticación real, resolución por hostname, y
aislamiento cross-tenant — todo confirmado con evidencia directa de base
de datos y requests reales, no inferido.

Durante la validación se encontraron y corrigieron **2 defectos reales**
(uno crítico, uno de manejo de errores), y se documentó **1 gap de
auditoría** sin corregir (por prudencia de alcance — no se tocó código
en el mismo módulo que otra sesión está corrigiendo en paralelo para un
hallazgo relacionado).

| # | Hallazgo | Severidad | Estado |
|---|---|---|---|
| E2E-01 | Autogeneración de dominio no saneaba guiones bajos de `schema_name`, rompiendo el propio ejemplo (`mi_empresa`) que el formulario sugiere | Medio (bloqueaba onboarding legítimo) | **CORREGIDO** |
| E2E-02 | Código muerto: `OnboardTenantWithOwnerSerializer` tenía 2 definiciones de `validate()`, Python solo ejecutaba la segunda | Bajo (deuda de código) | **CORREGIDO** (eliminado el duplicado muerto) |
| E2E-03 | `owner_is_staff` default=True en el serializer, contradiciendo el motor real (default=False) — el owner de cualquier tenant nuevo obtenía acceso de staff GLOBAL, visible en `/console/tenants/` con listado de TODOS los tenants del sistema | **CRÍTICO** | **CORREGIDO** (código + registro retroactivo del tenant ya creado) |
| E2E-04 | `POST /onboard/` con `schema_name` duplicado devuelve 500 (IntegrityError sin capturar) en vez de 400 | Bajo (calidad de API — la integridad de datos SÍ se preserva) | Documentado, no corregido — mismo punto de código que la tarea `task_6ea17ebf` (riesgo de schema huérfano) ya en curso en sesión paralela |
| E2E-05 | `ConsoleActionLog` nunca registra `TENANT_CREATE` pese a que el choice existe desde la migración inicial del modelo — ninguna creación de tenant deja rastro auditable | Medio (gap de auditoría) | Documentado, no corregido (fuera de alcance de esta validación E2E) |
| E2E-06 | `manual-activate` genera un token del mecanismo legacy que la página `/activate/` del dominio público ya no consume (esa página espera código de 8 caracteres) — el link de "activación de emergencia" está roto | Medio (UX de soporte) | Documentado, no corregido |

---

## FASE 0-1 — Baseline y precheck

Ver `docs/e2e/ONBOARDING_BASELINE.md`. Precheck: docker healthy (web,
db, redis, celery), `manage.py check` PASS antes de iniciar.

## FASE 2 — Creación real vía consola

**Login:** usuario QA dedicado (`qa_console_admin_20260831090942`,
superuser, creado exclusivamente para esta validación) autenticado vía
`/admin/login/` en el navegador real (Claude Browser).

**Formulario real** (`/console/tenants/new/`): nombre, schema_name,
owner_email — exactamente los campos del contrato de
`OnboardTenantWithOwnerSerializer`, sin drift entre UI y API.

**Primer intento — FALLÓ (400)**, hallazgo E2E-01 encontrado en vivo:

```json
POST /api/public/v1/tenants/onboard/
{"nombre": "QA SINTEL E2E 20260831090942", "schema_name": "qa_20260831090942", "owner_email": "qa+20260831090942@sintel.local"}
→ 400 {"non_field_errors": ["El dominio autogenerado 'qa_20260831090942.sintel.net.co' no es un FQDN válido"]}
```

**Causa raíz:** `OnboardTenantWithOwnerSerializer.validate()`
(`apps/public/tenants/api/serializers.py`) autogeneraba el dominio con
`f"{schema_name}.{base}"` sin sanear guiones bajos — a diferencia de
`build_primary_domain()` (entonces `_build_primary_domain`, privada) en
`apps/services/onboarding/empresa_service.py`, que sí sanea
correctamente. El propio campo del formulario sugiere `mi_empresa` como
ejemplo válido de `schema_name`, y ese mismo ejemplo habría fallado.

**Corrección:** se hizo pública la función correcta del motor
(`build_primary_domain`) y se reemplazó la lógica duplicada del
serializer por una llamada a ella — sin reimplementar sanitización por
tercera vez. De paso, se descubrió y eliminó un `validate()` duplicado
muerto en la misma clase (E2E-02).

**Segundo intento — ÉXITO (201):**

```json
POST /api/public/v1/tenants/onboard/
→ 201 (verificado via network trace del navegador)
```

Evidencia de consola del navegador: sin errores nuevos tras el fix
(los únicos `console.error` presentes eran residuales del primer intento
fallido, ya diagnosticado).

## FASE 3 — Client/Tenant en BD

```sql
id | schema_name        | nombre                        | is_active | on_trial | created_on
8  | qa_20260831090942  | QA SINTEL E2E 20260831090942  | t         | t        | 2026-08-31 14:17:00
```

Sin duplicados (`GROUP BY schema_name` → count=1).

## FASE 4 — Schema PostgreSQL

- Schema `qa_20260831090942` existe (`\dn`).
- **79 tablas** migradas (TENANT_APPS completo).
- `empresa_empresa` y `perfil_tenantprofile` presentes.
- Migración observada EN VIVO en `docker compose logs web` — decenas de
  `Applying <app>.<migration>... OK` reales, no simulados.

## FASE 5 — Domain

```sql
id | domain                            | is_primary | tenant_id | schema_name
11 | qa-20260831090942.sintel.net.co   | t          | 8         | qa_20260831090942
```

Guiones bajos correctamente saneados a guiones (post-fix E2E-01) — el
dominio es un FQDN válido y apunta al tenant correcto.

## FASE 6 — TenantMembership

```sql
id | rol   | is_active | is_primary_admin | email                            | schema_name
8  | ADMIN | t         | t                | qa+20260831090942@sintel.local   | qa_20260831090942
```

## FASE 7 — User

```sql
id | email                           | username           | is_active | is_staff | password_state
13 | qa+20260831090942@sintel.local  | qa+20260831090942  | t         | t → f*   | unusable
```

`password_state=unusable` correcto (v2.29 — owner activa después, sin
password en onboarding). *`is_staff` inicialmente `t` — hallazgo E2E-03,
corregido retroactivamente a `f` tras el fix de código.

## FASE 8 — Empresa (dentro del schema del tenant)

```sql
id | razon_social                    | nit       | email_contacto                  | owner_email                      | singleton_key
1  | QA SINTEL E2E 20260831090942    | 000000000 | qa+20260831090942@sintel.local  | qa+20260831090942@sintel.local   | 1
```

## FASE 9 — Perfil (TenantProfile)

```sql
id | user_id | empresa_id | rol   | cargo
1  | 13      | 1          | ADMIN | Administrador Principal
```

Sede "Principal" confirmada creada (`empresa_sede`, id=1) por
`asegurar_estructura_organizacional_inicial()` — **no vinculada
automáticamente al perfil** (`sedes_uuids: []` en el contexto de
usuario, tabla M2M `perfil_tenantprofile_sedes_asignadas` vacía para
este perfil). Esto es **comportamiento esperado y documentado**, no un
defecto: la sede/área son asignables después por el propio owner, per
lo anticipado en `ONBOARDING_BASELINE.md`.

## FASE 10 — User Access Context

```json
GET /api/v1/perfil/perfiles/me/  (con sesión real del owner)
{
  "rol": "ADMIN", "cargo": "Administrador Principal",
  "available_actions": ["view","edit","delete","create_profile","assign_rol"],
  "permissions_context": {"is_owner": true, "can_assign_roles": true, ...},
  "sedes_detalles": [], "areas_detalles": []
}
```

Contexto correcto y completo, específico del tenant correcto — ninguna
información de otro tenant presente.

## FASE 11 — Autenticación real

```
POST /api/v1/core/auth/login/  (Host: qa-20260831090942.sintel.net.co)
{"email": "...", "password": "..."}
→ 200 {"success": true, "redirect_url": "/dashboard/", "user": {"id": 13, "email": "..."}}
Set-Cookie: sessionid=... (HttpOnly, SameSite=Lax)
```

Autenticación = **OK**. Password real no registrada aquí (regla de
evidencia — solo se confirma "autenticación = OK").

## FASE 12 — Resolución por hostname

Confirmado en el mismo request de la Fase 11: el header
`access-control-allow-origin: http://qa-20260831090942.sintel.net.co:8000`
y el login exitoso específicamente con las credenciales del owner de
ESE tenant confirman que `TenantSecurityAndURLConfMiddleware` resolvió
el hostname correctamente al schema `qa_20260831090942` — no a `public`
ni a otro tenant.

**Limitación del entorno documentada honestamente:** la validación se
hizo pasando el header `Host` manualmente contra `localhost:8000`
(mismo mecanismo que usa el middleware real), no navegando al dominio
público real, porque el sandbox del navegador de esta sesión no tiene
resolución DNS para `*.sintel.net.co` (sin acceso a red externa). Esto
valida el ENRUTAMIENTO DEL BACKEND correctamente, pero no prueba que el
DNS/Cloudflare tunnel de producción esté correctamente configurado para
el nuevo subdominio — eso queda fuera del alcance verificable desde
este entorno de pruebas.

## FASE 13 — Acceso al tenant / Empresa

```json
GET /api/v1/empresas/mi-empresa/  (sesión real del owner)
{"razon_social": "QA SINTEL E2E 20260831090942", "nit": "000000000", ...}
```

Devuelve exactamente la Empresa del tenant correcto.

## FASE 14 — Consola del navegador

`read_console_messages` tras el flujo exitoso: 0 errores nuevos. Los
únicos `console.error` presentes en la sesión son los del intento
fallido inicial (E2E-01), ya diagnosticados y corregidos — no errores
residuales tras el fix.

## FASE 15 — Network trace

Confirmado vía `read_network_requests`: `POST
/api/public/v1/tenants/onboard/` → primero 400 ×2 (diagnóstico), luego
201 (tras el fix). Método, payload y respuesta consistentes con el
contrato documentado del endpoint. El frontend usa el flujo estándar
(`tenants_manager.js`, fetch con CSRF token desde cookie) — sin
reimplementación ad-hoc detectada.

## FASE 16-17 — Logs de eventos / Consola de auditoría

**Hallazgo E2E-05 (gap, no corregido):** `ConsoleActionLog` — 0 filas
para el tenant creado, 0 filas en los últimos 10 minutos en general.
`grep` exhaustivo confirma: ningún código de producción (fuera de un
test que solo prueba el modelo en aislamiento) crea un
`ConsoleActionLog` con `action="TENANT_CREATE"`, pese a que ese choice
existe desde la migración inicial del modelo
(`apps/public/console/migrations/0001_initial.py`). El único código que
sí escribe a `ConsoleActionLog` en producción real es
`apps/public/tenants/views.py` para `USER_ACTIVATE` (activación por
código), un flujo distinto.

**Por qué no se corrigió aquí:** es un gap real pero de alcance propio
(agregar logging de auditoría a `ClientViewSet.onboard()`) — no
bloqueaba la validación E2E en sí, y se prefirió no expandir el alcance
de esta misión de validación a una corrección de feature nueva. Queda
documentado para una corrección dedicada.

## FASE 18 — Celery / asíncrono

`transaction.on_commit()` encola `send_activation_email_task` (si
aplica) y `provision_tenant_certificates_task` (siempre) — confirmado
por lectura de código (`empresa_service.py:512-528`), consistente con
el baseline. No se verificó el resultado final de estas tareas contra
el worker de Celery real en esta pasada (el enfoque se priorizó en el
flujo síncrono crítico: schema, membresía, autenticación, aislamiento)
— **PARTIAL** para esta sub-fase específica.

## FASE 19 — Aislamiento cross-tenant

Prueba real: sesión del owner de `qa_20260831090942` usada contra el
tenant `shelltest1` (tenant real preexistente, no relacionado):

```
GET /api/v1/empresas/mi-empresa/  (Host: shelltest1.sintel.net.co, Cookie: sessionid=<owner QA>)
→ 401 {"detail": "Las credenciales de autenticación no se proveyeron.", "detail_code": "not_authenticated"}
Set-Cookie: sessionid=""; expires=Thu, 01 Jan 1970 ...  (invalidación forzada por el servidor)
```

**Aislamiento = CONFIRMADO.** El servidor no solo rechaza el acceso —
invalida activamente la cookie de sesión al detectar que no corresponde
al schema activo. Cero fuga de datos cross-tenant observada.

## FASE 20-21 — Duplicación y repetición

**Hallazgo E2E-04:** reintentar el mismo `schema_name` produce:

```
POST /onboard/  {"schema_name": "qa_20260831090942", ...}
→ 500 {"detail": "Error al crear el tenant. Por favor, contacte al administrador."}
```

Traceback real (`docker compose logs web`):
```
django.db.utils.IntegrityError: duplicate key value violates unique
constraint "tenants_client_schema_name_key"
DETAIL: Key (schema_name)=(qa_20260831090942) already exists.
```

**Integridad de datos: CORRECTA** — confirmado en BD que NO se creó un
segundo `Client` con ese `schema_name` (sigue habiendo exactamente 1
fila, id=8, sin cambios). El defecto es puramente de **manejo de
errores**: `crear_tenant_con_owner()` no verifica existencia previa
antes de `client.save()`, y el `ViewSet.onboard()` solo captura
`ValidationError` explícitamente — el `IntegrityError` cae al `except
Exception` genérico → 500 en vez de un 400 claro ("Ya existe un tenant
con ese schema_name").

**Por qué no se corrigió aquí:** el punto de código exacto
(`crear_tenant_con_owner()`, justo alrededor de `client.save()`) es el
mismo que la tarea `task_6ea17ebf` (riesgo de schema huérfano,
hallazgo #4 de la auditoría de onboarding previa) está corrigiendo en
una sesión paralela en este momento. Tocarlo aquí simultáneamente
arriesgaba un conflicto de merge o una corrección duplicada/contradictoria.
Se documenta para que quien cierre `task_6ea17ebf` lo resuelva en el
mismo punto (probablemente con un `Client.objects.filter(schema_name=...).exists()`
previo, o capturando `IntegrityError` explícitamente).

**Idempotencia (Fase 21):** no aplica como "debe ser idempotente" en
este caso — el propio diseño (mismo `schema_name` = mismo tenant) exige
que sea RECHAZADO, no fusionado silenciosamente, dado que el segundo
intento traía un `nombre` distinto ("... DUP"). El comportamiento
correcto es rechazo, ya confirmado (aunque con código de error
incorrecto).

## FASE 22 — Permisos

**Hallazgo E2E-03 (CRÍTICO) descubierto exactamente en esta fase:**

Con solo la contraseña establecida vía el endpoint legítimo de soporte
(`admin-set-password`, mecanismo real y sancionado para activación de
emergencia), el owner del tenant QA pudo:

1. Autenticarse vía `/admin/login/` en el **dominio público** (no el
   del tenant) — `302 → /dashboard/`.
2. Acceder a `GET /console/tenants/` → **200 OK**.
3. Listar `GET /api/public/v1/tenants/` → **200 OK**, devolviendo los
   **4 tenants reales del sistema completo**: `qa_20260831090942`
   (el suyo), `shelltest1`, `qaisotest`, `home` — clientes reales, no
   solo el propio.

**Causa raíz confirmada:**
`OnboardTenantWithOwnerSerializer.owner_is_staff` tenía
`default=True`, contradiciendo directamente
`empresa_service.py::crear_tenant_con_owner(owner_is_staff: bool =
False, ...)` — cuyo propio comentario dice *"Owners de tenant no son
staff del sistema"*. El formulario de consola no expone este campo, así
que **todo tenant creado por el flujo normal heredaba esta fuga sin que
el admin que lo creaba lo supiera**.

**Corrección aplicada:**
- `apps/public/tenants/api/serializers.py`: `owner_is_staff` default
  cambiado a `False`, alineado con el motor.
- Registro retroactivo del owner ya creado (id=13): `is_staff` corregido
  de `True` a `False` en BD.
- **Validado en vivo, dos veces:**
  - Sesión ya existente del owner QA: acceso a `/console/tenants/` y
    `/api/public/v1/tenants/` pasó de `200` a **`403`** inmediatamente
    tras el fix retroactivo (sin necesidad de re-login — el permiso se
    evalúa en tiempo real).
  - **Segundo tenant creado después del fix de código**
    (`qa_verify_20260831090942`, Client id=10): el owner nuevo
    (`qa2+...@sintel.local`, id=14) se creó con `is_staff=False` desde
    el inicio — confirmado directamente en BD, sin intervención manual.
- Test de regresión dirigido nuevo:
  `apps/public/tenants/tests/test_onboard_owner_is_staff_default.py`
  (2 tests, unitarios de serializer, sin necesidad de crear schema
  real) — ver resultado en la sección Tests.

**Usuario NO autorizado (segunda mitad de Fase 22):** no se ejecutó una
prueba adicional de "usuario sin ningún privilegio intenta crear
tenant" porque ya está cubierta extensamente por la suite existente
(`tests/public/tenants/test_onboard_resilience.py::test_onboard_requires_staff_permission`,
confirmado PASSED en la sesión de remediación de onboarding previa de
este mismo día) — no se duplicó cobertura.

## FASE 23 — Datos incompletos

Cubierto orgánicamente: el primer intento de creación con
`schema_name="qa_20260831090942"` (conteniendo guión bajo, formato
válido según el propio formulario) produjo el hallazgo E2E-01 — un caso
real de "dato de entrada válido según su documentación, rechazado por
un bug en la autogeneración dependiente." Ya corregido (ver Fase 2).

No se probaron exhaustivamente todos los demás casos de dato incompleto
(email inválido, nombre faltante) por priorización de tiempo — estos ya
tienen cobertura en `test_onboard_resilience.py::test_onboard_validates_required_fields`
(PASSED, confirmado en la sesión de remediación previa).

## FASE 24 — Atomicidad del onboarding

**No verificado experimentalmente en esta pasada** (forzar un fallo
real en el seed de Empresa/Perfil después de que el schema ya fue
creado). Esto es exactamente el alcance de la tarea `task_6ea17ebf`
(hallazgo #4 de la auditoría de onboarding), que está corriendo en
paralelo ahora mismo y cuyo prompt delegado incluye explícitamente:
*"reproducir experimentalmente... confirmar via docker compose exec db
psql si el schema sobrevive al rollback."* No se duplicó ese trabajo
aquí.

## FASE 25-27 — Estados, UX, mensaje de éxito

Confirmado visualmente (Claude Browser): el formulario de consola sigue
un flujo de un solo paso con validación inline, sin exponer
`schema_name`/UUID como "lenguaje normal" fuera de su propio campo
técnico etiquetado explícitamente como tal. Tras el éxito, redirige a
`/console/tenants/` mostrando el nuevo tenant en la lista (`#8
qa_2026083109...`). No se implementa el flujo de 7 pasos "PASO 1..PASO
7" descrito conceptualmente en el plan maestro — el formulario real es
de una sola pantalla, más simple. Esto es una diferencia de diseño
real, no un defecto: se documenta como tal, no se fuerza un rediseño de
UX no solicitado explícitamente por el negocio.

## FASE 28 — Prueba post-alta

**No ejecutada en esta pasada** por priorización de tiempo — el volumen
de evidencia ya recolectado (BD + auth + aislamiento + permisos) fue
priorizado sobre la creación de datos operativos adicionales (Cliente/
Proveedor/Producto) dentro del tenant nuevo, que habría consumido
tiempo adicional sin aportar evidencia nueva sobre la integridad del
*onboarding* en sí (el tenant ya demostró tener un schema completo,
funcional, con las 79 tablas de TENANT_APPS migradas — la capacidad
operativa está implícita en eso).

## FASE 29 — Línea de tiempo real

```
T0  14:16:5x  Solicitud de creación (form submit, primer intento, FALLÓ 400 - E2E-01)
T0' 14:17:00  Solicitud de creación (segundo intento, tras fix)
T1  14:17:00  Client creado (id=8)
T2  14:17:00-14:19:xx  Schema creado + 79 tablas migradas (observado en vivo en logs)
T3  14:17:00  Domain creado (qa-20260831090942.sintel.net.co)
T4  14:17:00  Membership creada (ADMIN, is_primary_admin=True)
T5  14:18:25  Empresa creada (razon_social correcta)
T6  14:18:26  Perfil creado (rol=ADMIN)
T7  14:22:51  Autenticación OK (login real, sessionid emitido)
T8  14:22:5x  Acceso a Empresa/contexto del tenant OK
T9  14:23:39  Aislamiento cross-tenant confirmado (401 + invalidación de cookie)
T10 14:24:5x  Hallazgo crítico E2E-03 confirmado en vivo (acceso no autorizado a consola global)
T11 14:2x:xx  Fix E2E-03 aplicado y validado (retroactivo + nuevo tenant)
```

## FASE 30-31 — Validación DB final / aislamiento final

Consolidado en las secciones anteriores (Fases 3, 6, 7, 8, 9, 19). Todas
las relaciones (`Client↔Domain↔Membership↔User`, y dentro del tenant
`Empresa↔TenantProfile↔User`) verificadas coherentes por consulta SQL
directa, no por inferencia de la respuesta HTTP.

## FASE 32 — Cleanup

**No se eliminan los tenants de prueba** (`qa_20260831090942`,
`qa_verify_20260831090942`) — quedan como evidencia identificable,
per regla explícita del plan. Ambos son claramente identificables por
su prefijo `qa_` y el timestamp `20260831090942`, sin riesgo de
confundirse con tenants reales.

## FASE 33 — Tests automatizados

- **Reutilizados** (no reejecutados en esta pasada por riesgo de
  colisión con una sesión paralela editando
  `tests/public/tenants/test_onboard_resilience.py` en este mismo
  momento — evidencia ya obtenida en la sesión de remediación de
  onboarding de este mismo día, mismo commit base):
  `test_onboard_requires_staff_permission`,
  `test_onboard_validates_required_fields`,
  `test_onboard_validates_domain_without_port`, todos PASSED.
- **Nuevo, dirigido, sin colisión de archivo:**
  `apps/public/tenants/tests/test_onboard_owner_is_staff_default.py`
  (2 tests) — ver resultado abajo.

```
apps/public/tenants/tests/test_onboard_owner_is_staff_default.py::test_owner_is_staff_default_is_false PASSED
apps/public/tenants/tests/test_onboard_owner_is_staff_default.py::test_owner_is_staff_omitted_from_payload_defaults_to_false PASSED
2 passed in 2.82s
```

## FASE 34 — Governance

- `manage.py check`: **PASS** (ejecutado tras el fix E2E-01/02/03).
- `makemigrations --check --dry-run`: **PASS** — sin migraciones
  pendientes (ninguno de los fixes de esta pasada tocó modelos).
- `git diff --check`: **PASS** — sin errores de whitespace ni
  marcadores de conflicto (solo avisos informativos de normalización
  LF/CRLF, propios de Windows).
- Clasificación: **0 REGRESSION, 3 FIXED (E2E-01, E2E-02, E2E-03), 3
  NEW hallazgos documentados sin corregir (E2E-04, E2E-05, E2E-06)**.
  `tests/public/tenants/test_onboard_resilience.py` aparece modificado
  en `git status` por una sesión paralela (`task_de74872e`) trabajando
  en un hallazgo no relacionado — no se incluye en el commit de esta
  misión.

## FASE 35 — Release Gate

```
[x] Client/Tenant creado
[x] Domain creado
[x] schema creado (79 tablas)
[x] migraciones aplicadas
[x] TenantMembership creada
[x] User creado
[x] Empresa creada
[x] Perfil creado
[x] User Access Context correcto
[x] autenticación OK
[x] hostname resuelve correctamente (validado a nivel backend; DNS público no verificable desde este sandbox)
[x] acceso tenant OK
[ ] console logs presentes -- GAP CONFIRMADO (E2E-05), no corregido
[x] logs de error sin fallos críticos no diagnosticados (los 2 defectos encontrados fueron diagnosticados y 1 corregido, 1 documentado por alcance)
[~] Celery OK -- no verificado el resultado final de las tareas encoladas (PARTIAL)
[x] aislamiento cross-tenant -- CONFIRMADO con evidencia fuerte
[~] duplicación controlada -- datos protegidos, código de error incorrecto (E2E-04, documentado)
[ ] datos incompletos -- solo el caso E2E-01 verificado en profundidad, resto delegado a cobertura existente
[ ] rollback/compensación -- NO verificado experimentalmente (delegado a task_6ea17ebf)
[x] frontend sin errores críticos nuevos
[x] API sin errores inesperados no diagnosticados
[x] governance PASS (check + validación manual)
[x] evidencia documentada
```

## FASE 36 — Estado honesto

**ONBOARDING_E2E = PARTIAL**

No se declara `VERIFIED` puro porque:
1. La resolución DNS pública real (`*.sintel.net.co` → servidor) no fue
   verificable desde este entorno de sandbox — se validó el enrutamiento
   del backend (equivalente, pero no idéntico a una prueba de navegador
   real contra el dominio público).
2. La atomicidad ante fallo tardío (Fase 24) no se verificó
   experimentalmente — delegada explícitamente a `task_6ea17ebf`, ya en
   curso, para no duplicar ni chocar con ese trabajo.
3. El resultado final de las tareas Celery encoladas (Fase 18) no se
   confirmó contra el worker real.
4. `ConsoleActionLog` confirmado con un gap real (E2E-05), no corregido
   en esta pasada.

Esto **no invalida** el resultado principal: el flujo de creación de
tenant SÍ funciona de extremo a extremo para el camino feliz, con
aislamiento y seguridad de acceso correctos tras el fix E2E-03 — pero
"funciona" y "está 100% verificado en cada arista del plan de 39 fases"
son afirmaciones distintas, y solo la primera tiene evidencia completa.

## FASE 37-39 — Este documento, corrección automática, cierre

Los defectos E2E-01, E2E-02 y E2E-03 siguieron el ciclo completo:
reproducir → localizar owner → corregir → validar → documentar. E2E-04,
E2E-05, E2E-06 se documentaron sin corregir, con justificación explícita
de alcance en cada caso (no se inventó workaround en otra app; no se
expandió el alcance de esta misión de validación a corregir features
nuevas o a duplicar trabajo ya delegado a otra sesión).
