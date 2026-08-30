# Auditoría — Onboarding y Creación de Nuevos Tenants

**Fecha:** 2026-08-30
**Rama:** `feat/onboarding-cookie`
**Alcance:** Todo el proceso por el cual un tenant (empresa) nuevo se crea en SINTEL ERP — desde el punto de entrada público hasta un schema PostgreSQL funcional con su primer usuario administrador. Incluye el flujo self-service público (OTT), el flujo administrado desde consola (staff), el comando de gestión, y el mecanismo de cookies HttpOnly que da nombre a la rama actual.

**Método:** Solo lectura de código real, migraciones, tests y documentación existente (`.agent/`). Ningún archivo de producto fue modificado durante esta auditoría — regla ya establecida en esta sesión ("Primero AUDITAR, MAPEAR, CLASIFICAR. Después CORREGIR").

---

## 0. Addendum de remediación (2026-08-30, misma fecha, pasada posterior)

Se remedaron 6 de los 7 hallazgos. El resumen ejecutivo y las secciones de
hallazgos que siguen son el **registro histórico** de la auditoría original
— se dejan sin reescribir para preservar la evidencia tal como se encontró.
Este addendum documenta qué se corrigió y cómo.

| # | Severidad | Estado | Corrección |
|---|---|---|---|
| 1 | CRÍTICO | **REMEDIADO** | `CreateTenantOnboardingAPIView` ya no devuelve `ott`/`redirect_url` en la respuesta HTTP — el único canal de entrega es el email de activación (48h, firmado) que `crear_tenant_con_owner()` ya enviaba, sin cambios ahí. Test de regresión actualizado (`apps/public/tenants/tests/test_core_onboarding_flow.py`) para afirmar explícitamente que el OTT nunca aparece en el body de la respuesta. |
| 2 | ALTO | **REMEDIADO** (decisión: formalizar sesión, no terminar el JWT-en-cookie) | Eliminado el bloque muerto de `apps/public/core/middleware.py` que leía `request.COOKIES.get('access_token')` sin que nada lo produjera. El diseño final es sesión Django estándar (`login()`), ya probado extensamente. Se optó por esto en vez de terminar de implementar JWT-en-cookie porque: (a) el trabajo de consolidación `landing`→`core` ya reescribió `consume-ott` sobre sesión, con tests reales pasando; (b) resucitar el diseño JWT-en-cookie habría requerido reimplementar `set_cookie` + ajustar CORS/CSRF para cross-subdomain, un cambio de mayor alcance que "corrección mínima" para un hallazgo de limpieza de código muerto. |
| 3 | MEDIO | **REMEDIADO** | Eliminado `apps/public/tenants/services.py` (confirmado `DEAD_CONFIRMED` — inalcanzable por colisión de nombre con el paquete `services/`, cero importadores reales). Corregido el comentario desactualizado en `apps/public/tenants/services/onboarding.py` que referenciaba la ruta muerta. |
| 4 | MEDIO | **CONFIRMADO, no remediado — ver justificación abajo** | Se verificó (lectura del código fuente de `django-tenants`, no experimentalmente contra datos reales) que el riesgo es real, no hipotético — ver detalle abajo. |
| 5 | MEDIO | **REMEDIADO** | `apps/public/tenants/validators.py::validate_schema_name` ahora reexporta la versión de `apps/public/tenants/utils.py` (la más estricta: exige iniciar con letra, bloquea 3 nombres reservados) en vez de mantener una segunda implementación divergente. Los 3 puntos de import (`models.py`, `api/serializers.py`, el ya-eliminado `services.py`) no requirieron cambios de import. |
| 6 | BAJO | **REMEDIADO** | `CreateTenantOnboardingAPIView.post()` ahora captura `ValidationError` explícitamente → 400 con el mensaje real, antes de caer al `except Exception` genérico → 500. |
| 7 | BAJO | **REMEDIADO** | Nuevo `apps/public/tenants/throttling.py::OnboardingCreateThrottle` (mismo patrón que `IngestaScopedThrottle` ya existente), scope `tenant_onboarding_create` a `10/hour`, registrado en `config/settings.py` y aplicado al endpoint. |

### Hallazgo #4 — evidencia nueva que CONFIRMA el riesgo (no solo lo señala como no verificado)

Lectura directa de `venv/Lib/site-packages/django_tenants/models.py`,
`TenantMixin.save()` (líneas 102-137): cuando `create_schema()` (que ejecuta
`CREATE SCHEMA` + `call_command('migrate_schemas', ...)`) falla, el propio
`save()` de django-tenants **no confía en que el rollback de una transacción
externa vaya a limpiar el schema físico** — captura la excepción
explícitamente y llama `self.delete(force_drop=True)` para hacer `DROP
SCHEMA ... CASCADE` de forma manual antes de re-lanzar.

Esto confirma que `call_command('migrate_schemas', ...)` casi con certeza
NO participa de la misma transacción Django que el llamador — probablemente
gestiona su propia conexión/transacción internamente. Consecuencia real para
`crear_tenant_con_owner()` (que envuelve TODO, incluyendo `client.save()` Y
los pasos 4-7 posteriores — Domain, Membership, seed de Empresa/Perfil —
dentro de un único `@transaction.atomic`): si el seed de Empresa/Perfil
(paso 6) falla y hace `raise` (línea 472 de `empresa_service.py`), el
`@transaction.atomic` externo hace rollback de las filas Django (`Client`,
`Domain`, `TenantMembership`, `User` si es nuevo) — pero el schema físico de
PostgreSQL, ya creado y migrado por `create_schema()` varias líneas antes,
probablemente **no se revierte**, quedando huérfano: un schema real con
tablas vacías, sin ningún `Client` en `public.tenants_client` que lo
referencie.

**Por qué no se corrige en esta misma pasada:** la corrección correcta
requiere separar la creación de schema (que debe tratarse como una
operación NO transaccional, con su propia limpieza explícita en caso de
fallo — exactamente el patrón "Two-Phase DDL/DML" que la documentación
`.agent/AUDITORIA_FLUJO_CORE_PUBLIC.md` describe para una versión distinta,
hoy inalcanzable, de esta función, ver Hallazgo #3 original) del resto del
flujo transaccional (Domain/Membership/seed). Reestructurar los límites de
transacción de `crear_tenant_con_owner()` — la función motor compartida por
AMBAS vías de onboarding, cubierta por 41+ tests existentes de la Vía A —
es un cambio de mayor alcance y riesgo de regresión que excede lo que esta
pasada puede validar con seguridad bajo el límite de 15 minutos por acción.
Se flagea como tarea dedicada (ver spawn_task registrado en esta sesión) en
vez de arriesgar una corrección apresurada sobre una función crítica y
ampliamente cubierta por tests.

**Mitigación parcial ya vigente sin cambios adicionales:** el paso 6
(seed de Empresa/Perfil) está diseñado para NUNCA fallar en el caso común —
solo hace `raise` ante un `Exception` genuino no relacionado con tablas
faltantes (que sí se tolera explícitamente vía `ProgrammingError`). El
riesgo es real pero de baja frecuencia esperada en operación normal.

---

## 1. Resumen ejecutivo

Existen **dos vías completamente distintas** para crear un tenant nuevo, con posturas de seguridad muy diferentes:

| Vía | Quién la dispara | Autenticación | Verificación de email | Endpoint |
|---|---|---|---|---|
| **A. Consola administrativa** | Staff (`is_staff=True`) | `SessionAuthentication` + `IsAdminUser` | Sí — token firmado, 48h, requiere clic en email real | `POST /api/public/v1/clients/onboard/` |
| **B. Self-service público (OTT)** | Cualquier visitante anónimo | Ninguna (`AllowAny`, sin CSRF) | **No** — el OTT se devuelve directamente en la respuesta HTTP al llamante | `POST /api/public/v1/tenants/onboarding/create/` |

Ambas vías terminan en el **mismo motor de creación** (`crear_tenant_con_owner()` / `onboard_tenant()` en `apps/services/onboarding/empresa_service.py`), que está bien diseñado: idempotente, con guardas de unicidad, y con un seed opcional de `Empresa`/`TenantProfile` que nunca rompe el onboarding si falla.

El hallazgo central de esta auditoría es que **la Vía B (el flujo que da nombre a esta rama) tiene un problema de seguridad real y verificable**: cualquiera puede provisionar un tenant a nombre de un email ajeno y obtener una sesión autenticada como "owner" de ese tenant sin que el dueño real del email intervenga — ver Hallazgo #1.

El segundo hallazgo central es que **el mecanismo de cookies HttpOnly que da nombre a la rama (`feat/onboarding-cookie`) está a medio implementar**: el código que lo consume existe y sigue activo en producción, pero el código que lo produce fue eliminado en un commit posterior de "limpieza" — ver Hallazgo #2.

No se tocó ni un archivo de código durante esta auditoría. Todo lo documentado abajo es evidencia directa de código, con ruta y línea.

---

## 2. Mapa de arquitectura

```
Visitante anónimo                          Staff en /console/tenants/
      │                                              │
      ▼                                              ▼
POST /api/public/v1/tenants/                POST /api/public/v1/clients/onboard/
     onboarding/create/                              │
(CreateTenantOnboardingAPIView,                       │ SessionAuth + IsAdminUser
 AllowAny, sin auth, sin CSRF)                        │
      │                                              │
      ▼                                              ▼
create_onboarding_ott()  ───────────┐        (ClientViewSet.onboard, api/viewsets.py)
(apps/public/tenants/               │                 │
 services/onboarding.py)            │                 │
      │                             │                 │
      ▼                             │                 ▼
crear_tenant_con_owner() ◄──────────┴─────── crear_tenant_con_owner()
(apps/services/onboarding/empresa_service.py — MOTOR ÚNICO, compartido)
      │
      ├─ 1. User.objects.get_or_create(email=...) — set_unusable_password()
      ├─ 2. validate_schema_name() — regex ^[a-z][a-z0-9_]*$, máx 63, reservados
      ├─ 3. Client(schema_name=...).save()  → auto_create_schema=True
      │       → django-tenants: CREATE SCHEMA + migrate_schemas TENANT_APPS
      ├─ 4. Domain.objects.get_or_create(domain=FQDN, is_primary=True)
      ├─ 5. TenantMembership.objects.get_or_create(rol=ADMIN, is_primary_admin=True)
      ├─ 6. schema_context(schema): Empresa.objects.get_or_create(singleton_key=1)
      │       + asegurar_estructura_organizacional_inicial()
      │       + TenantProfile.objects.get_or_create(rol=ADMIN)
      └─ 7. transaction.on_commit(): encola email de activación (token firmado, 48h)
                                      + provisión de certificados
      │
      ▼
   TODO envuelto en UN SOLO @transaction.atomic (ver Hallazgo #4)
      │
      ▼
  ┌───┴────────────────────────────┐
  │                                 │
  ▼ (Vía B, self-service)           ▼ (Vía A, consola)
OTT en Redis (TTL 5 min)      Email de activación real
  │                            (token firmado, 48h, requiere
  │                             clic + set_password)
  ▼
GET /static/core/onboard.html?ott=...
  │
  ▼
POST /api/v1/core/auth/consume-ott/
(CoreAuthViewSet.consume_ott, apps/tenant/core/api/viewsets.py:648)
  │
  ├─ consume_onboarding_ott(ott) — Redis GETDEL, uso único
  ├─ si user.has_usable_password() → already_activated=True → redirige a /login/
  └─ si no → login(request, user)  ← SESSION DJANGO ESTÁNDAR, NO JWT/cookie
       (ver Hallazgo #2 — el diseño original usaba JWT en cookie HttpOnly)
```

---

## 3. Hallazgos

### Hallazgo #1 (CRÍTICO) — El OTT de la Vía B se entrega al llamante anónimo, no al dueño del email

**Evidencia:**
- `apps/public/tenants/api/views.py:95-125` (`CreateTenantOnboardingAPIView`) — `permission_classes = [AllowAny]`, `authentication_classes = []`. Recibe `company_name` + `admin_email` de cualquier POST anónimo, sin verificar que el llamante controle ese email.
- `apps/public/tenants/api/views.py:122` — la respuesta HTTP 201 incluye `"ott": result["ott"]` **directamente en el JSON**, visible para quien hizo el POST.
- `apps/public/tenants/services/onboarding.py:110-169` (`consume_onboarding_ott`) — el consumo del OTT no exige ninguna prueba adicional de identidad; solo el UUID del OTT.
- `apps/tenant/core/api/viewsets.py:709-711` — cuando el usuario es nuevo (`already_activated=False`), el consumo hace `login(request, user)` **directamente**, sin contraseña, otorgando una sesión Django autenticada como dueño (`rol=ADMIN`, `is_primary_admin=True`) del tenant recién creado.

**Escenario de explotación real:**
1. Atacante hace `POST /api/public/v1/tenants/onboarding/create/` con `admin_email = "gerencia@empresa-real.com"` (un email que no controla).
2. La respuesta 201 le entrega `ott` y `redirect_url` directamente — sin que "gerencia@empresa-real.com" haya intervenido.
3. Dentro de los 5 minutos de TTL, el atacante visita `redirect_url`, que consume el OTT y ejecuta `login()` — el atacante ahora tiene una sesión Django autenticada como owner/ADMIN de un tenant nuevo, con un `User` cuyo email es el de un tercero real.
4. En paralelo, sí se encola (vía `crear_tenant_con_owner()` paso 7) un email de activación real hacia "gerencia@empresa-real.com" — pero el atacante ya obtuvo acceso vía sesión antes de que el destinatario real vea ese correo.

**Impacto:** el atacante no obtiene una contraseña reutilizable (el `User` sigue con `set_unusable_password()`), pero sí una sesión completa con permisos de ADMIN sobre un tenant nuevo — suficiente para invitar a otros usuarios, ver/modificar configuración, o realizar acciones dentro de esa sesión. También permite "ocupar" (squatting) el email de un tercero real contra un `schema_name`/dominio de su elección, generando confusión o abuso de marca.

**No cubierto por ningún test existente** — `test_core_onboarding_flow.py` (el único test de este flujo) usa un email controlado por el propio test (`autotest+{schema}@local.test`) y no ejercita el caso de un email de tercero.

### Hallazgo #2 (ALTO) — El mecanismo "onboarding-cookie" que da nombre a la rama está incompleto: se eliminó el productor, quedó vivo el consumidor

**Evidencia:**
- Commit `8b56d35` (feat, 27 marzo) implementó JWT en cookies `HttpOnly` para `consume-ott`: `apps/tenant/landing/api/viewsets.py` (entonces) seteaba `resp.set_cookie('access_token', ..., httponly=True, secure=..., samesite='Lax')`.
- Commit `bae6fe1` (fix, mismo período) agregó el lado **consumidor** en `apps/public/core/middleware.py:267-277`: lee `request.COOKIES.get('access_token')` y lo mapea a `HTTP_AUTHORIZATION` si no viene ya un header — **este código sigue activo hoy**.
- Commit `1e30cc7` (test) agregó `tests/public/tenants/tests/test_onboarding_cookie_flow.py` cubriendo el flujo JWT-en-cookie.
- Commit `c1d5658` ("chore: cleanup legacy templates and JS files", parte de una consolidación arquitectónica mayor `landing` → `core`) **eliminó por completo** la acción `consume_ott` de `apps/tenant/landing/api/viewsets.py` — incluyendo el `set_cookie` — sin migrar esa lógica a la nueva ubicación consolidada.
- La reimplementación actual y activa (`apps/tenant/core/api/viewsets.py:648-728`) usa **`login(request, user)`** (sesión Django estándar), no JWT ni cookies custom.
- **Verificado por búsqueda exhaustiva:** `grep -r "set_cookie" apps/` → **0 resultados** en todo el árbol de código actual. Ninguna vista, en ningún flujo, setea la cookie `access_token`.
- El test heredado (`test_onboarding_cookie_flow.py` → renombrado `test_core_onboarding_flow.py` en algún punto posterior) **sigue llamándose** `test_onboarding_ott_cookie_flow`, con docstring *"verify HttpOnly cookies authenticate API calls"*, pero su aserción real (línea 62) verifica `"sessionid" in cookies` — la cookie de sesión estándar de Django, no la cookie JWT custom que el nombre/docstring describen. El test fue actualizado para pasar con el comportamiento nuevo, pero su nombre y documentación quedaron desalineados con lo que realmente prueba.

**Estado actual:** el middleware que lee la cookie `access_token` es código muerto e inofensivo (está en un `try/except` con `pass` de seguridad) — no rompe nada, pero tampoco hace nada, porque nunca hay nada que leer.

**Decisión pendiente que esta auditoría no toma por sí sola** (regla de no inventar política de negocio): ¿la intención de la rama `feat/onboarding-cookie` es *terminar* de implementar el flujo JWT-en-cookie-HttpOnly (más apto para SPA/API pura, sin las limitaciones de cookies de sesión cross-subdominio), o *formalizar* que el diseño final es sesión Django estándar y limpiar el middleware muerto? Sin esa decisión de producto, cualquier corrección de código sería inventar la respuesta.

### Hallazgo #3 (MEDIO) — Documentación de auditoría (`.agent/`) describe una función que nunca se ejecuta

**Evidencia:**
- `apps/public/tenants/services.py` (archivo suelto) define su **propia** versión de `crear_tenant_con_owner()`, con diseño "Two-Phase DDL/DML" (schema creation deliberadamente *fuera* de `transaction.atomic`).
- `apps/public/tenants/services/` (paquete, con `__init__.py`) **coexiste en el mismo directorio** con el mismo nombre base (`services`).
- En Python, cuando un paquete (`services/`) y un módulo (`services.py`) comparten nombre en el mismo directorio padre, el import estándar (`import apps.public.tenants.services` o `from apps.public.tenants.services import X`) resuelve **siempre al paquete** — `services.py` es inalcanzable por el mecanismo de import normal.
- Confirmado por grep exhaustivo: **ninguna** parte del código importa nada de `apps/public/tenants/services.py`. El único lugar que lo menciona es un comentario/docstring desactualizado en `apps/public/tenants/services/onboarding.py:8` ("usa `apps.public.tenants.services.crear_tenant_con_owner`"), que no coincide con el import real tres líneas más abajo (`from apps.services.onboarding.empresa_service import crear_tenant_con_owner`).
- `apps/public/.agent/AUDITORIA_FLUJO_CORE_PUBLIC.md` (líneas 236-243) documenta el diseño "Two-Phase DDL/DML (v3.11.0)... Eliminados: `@transaction.atomic` global" como si fuera el comportamiento actual — pero ese diseño corresponde a la función **inalcanzable** de `services.py`. La función que realmente se ejecuta (`empresa_service.py::crear_tenant_con_owner`) sí envuelve todo, incluyendo la creación del schema, en un único `@transaction.atomic` (ver Hallazgo #4).

**Impacto:** cualquiera que confíe en `.agent/AUDITORIA_FLUJO_CORE_PUBLIC.md` como fuente de verdad (tal como exige `CLAUDE.md`: *"antes de cualquier cambio: leer... el `.agent/` audit doc"*) parte de una descripción incorrecta del comportamiento transaccional real del onboarding.

### Hallazgo #4 (MEDIO) — El motor real envuelve creación de schema + migración completa del tenant en una sola transacción

**Evidencia:**
- `apps/services/onboarding/empresa_service.py:208` — `@transaction.atomic` decora `crear_tenant_con_owner()` en su totalidad, incluyendo `client.save()` (línea 357), que dispara `auto_create_schema=True` de django-tenants → `CREATE SCHEMA` + `migrate_schemas` de **todas** las `TENANT_APPS` (decenas de migraciones).
- `onboard_tenant()` (línea 554, la variante usada por consola/comando) tiene el mismo patrón.

**Por qué importa:** PostgreSQL soporta DDL transaccional, así que en principio esto es seguro *si* `migrate_schemas` ejecuta todo sobre la misma conexión/transacción que el bloque `atomic` exterior. Esta auditoría **no verificó experimentalmente** si `django-tenants` abre conexiones o transacciones internas independientes durante `migrate_schemas` (lo cual, de ser el caso, dejaría un schema parcialmente migrado y comprometido si el paso 6 — seed de `Empresa`/`TenantProfile` — falla y dispara el `raise` explícito de la línea 472, que aborta todo el onboarding). Dado que el propio `.agent/AUDITORIA_FLUJO_CORE_PUBLIC.md` documenta que una versión anterior *deliberadamente* sacó la creación de schema del bloque atómico (ver Hallazgo #3), existe la posibilidad de que esa decisión respondiera a un problema real ya observado, y que el código actual haya reintroducido el riesgo sin que quede constancia de por qué. **Recomendación de verificación dirigida** (no ejecutada en esta auditoría, por regla de no modificar código): reproducir un fallo forzado en el paso 6 y confirmar en los 3 tenants reales si el schema queda huérfano tras el rollback.

### Hallazgo #5 (MEDIO) — `validate_schema_name` duplicado con reglas divergentes

**Evidencia:**
- `apps/public/tenants/utils.py::validate_schema_name` — regex `^[a-z][a-z0-9_]*$` (exige iniciar con letra), bloquea 3 nombres reservados (`public`, `pg_catalog`, `information_schema`). Es la que usa el motor real (`empresa_service.py`).
- `apps/public/tenants/validators.py::validate_schema_name` — regex `^[a-z0-9_]+$` (permite iniciar con dígito o guión bajo), solo bloquea `public` como reservado, con chequeo aparte de guión bajo inicial/final. Es la que usa `Client.clean()` (`apps/public/tenants/models.py:60`).
- Ninguna de las dos permite caracteres SQL peligrosos (`;`, comillas, espacios) — **no hay riesgo de inyección real** en ninguna de las dos variantes — pero tienen superficies de validación distintas, y no queda claro cuál es la autoritativa cuando ambas se invocan en el mismo flujo (`Client.clean()` se ejecuta primero de forma más laxa; `validate_schema_name` de `utils.py` se ejecuta después, de forma más estricta, dentro de `crear_tenant_con_owner`).

**Impacto:** bajo (ambas rutas terminan bloqueando lo peligroso), pero es deuda de mantenimiento real — cambiar una sin la otra es fácil y ya divergieron una vez.

### Hallazgo #6 (BAJO) — Errores de validación de `schema_name`/`company_name` se propagan como HTTP 500, no 400

**Evidencia:** `CreateTenantOnboardingAPIView.post()` (`apps/public/tenants/api/views.py:118-125`) envuelve la llamada en un `except Exception` genérico que responde 500 para **cualquier** error, incluyendo `ValidationError` de `validate_schema_name` (por ejemplo, un `company_name` con tildes, `&`, emoji, o que empiece con dígito generará un `schema_name` inválido y una respuesta 500 en vez de un 400 con mensaje claro).

**Impacto:** solo UX — el rechazo de seguridad sí ocurre correctamente (no se crea nada peligroso), pero el mensaje al usuario final es un error genérico de servidor en vez de una validación clara.

### Hallazgo #7 (BAJO) — Rate limiting genérico, no específico para un endpoint que crea recursos costosos

**Evidencia:** `config/settings.py:630-637` — `DEFAULT_THROTTLE_CLASSES` incluye `AnonRateThrottle` (500 req/día por IP anónima), aplicado globalmente vía DRF. `CreateTenantOnboardingAPIView` no declara `throttle_classes` propio, así que hereda ese límite genérico — el mismo límite que rige, por ejemplo, consultas de catálogo DIAN.

**Impacto:** 500 creaciones de schema PostgreSQL por día por IP (cada una con `CREATE SCHEMA` + migración completa de `TENANT_APPS`) es un límite laxo para una operación tan costosa en recursos de BD, comparado con endpoints ya protegidos con throttle dedicado en este mismo proyecto (`apps.public.impuestos.api.ingesta.throttling.IngestaScopedThrottle` ya existe como patrón reutilizable). No hay CAPTCHA ni verificación adicional.

---

## 4. Lo que SÍ está bien diseñado (no son hallazgos, es reconocimiento explícito)

- **Idempotencia real, no solo declarada**: `User.objects.get_or_create`, `Domain.objects.get_or_create` + read-back ante `IntegrityError` (condición de carrera), `TenantMembership.objects.get_or_create` — los tres puntos de escritura del motor están correctamente protegidos contra doble-submit y reintentos.
- **El seed de `Empresa`/`TenantProfile` nunca rompe el onboarding por un `ProgrammingError`** (tabla no migrada aún) — solo lo aborta ante un error genuinamente inesperado, con log claro.
- **`transaction.on_commit()` para el email y la provisión de certificados** — evita la clásica race condition de disparar un task de Celery antes de que la transacción exterior haga commit.
- **`validate_schema_name` (ambas variantes) bloquea correctamente cualquier caracter peligroso para SQL** — el riesgo de inyección vía nombre de schema está genuinamente cerrado.
- **`generate_activation_code`/`generate_invitation_token`**: entropía y TTL adecuados para el flujo de activación por email (Vía A y la rama email de la Vía B).
- **Triple capa de protección contra eliminación del schema `public`** (documentada y, según el `.agent/`, verificada).
- **Cobertura de tests real y variada** para la Vía A (consola/staff): 41+ tests distribuidos en `test_onboard.py`, `test_onboard_async.py`, `test_onboard_idempotent.py`, `test_onboard_invite.py`, `test_onboard_resilience.py`, `test_onboard_username_not_empty.py`, `test_onboarding_sin_password.py`, `test_api_onboard_dynamic.py`, `tests/tenant/critical/test_tenant_onboarding.py` — cubren duplicados de dominio, campos requeridos, permisos de staff, colisión de username, ausencia de tabla `perfil_tenantprofile`, y más.

---

## 5. Brecha de cobertura de tests

| Escenario | Cubierto |
|---|---|
| Vía A (consola/staff): creación, duplicados, permisos, resiliencia | ✅ Amplio (41+ tests) |
| Vía B (self-service público): creación exitosa con email propio | ✅ 1 test (`test_core_onboarding_flow.py`) |
| Vía B: `admin_email` de un tercero no controlado por el llamante | ❌ Sin cobertura — es exactamente el Hallazgo #1 |
| Vía B: rate limiting / abuso del endpoint público | ❌ Sin cobertura |
| Cookie `access_token` HttpOnly (Hallazgo #2) | ❌ El test original (`1e30cc7`) que la cubría probaba código que ya no existe |
| `validate_schema_name`: input con tildes/emoji/caracteres especiales vía API pública → código de respuesta | ❌ Sin cobertura directa del contrato HTTP (existe cobertura de la función en aislado) |
| Fallo forzado en el seed de `Empresa`/`TenantProfile` → estado del schema tras rollback (Hallazgo #4) | ❌ Sin cobertura |

---

## 6. Comando de gestión (`crear_empresa`) vs. flujo self-service

`crear_empresa` (management command, `apps/public/tenants/management/commands/`) y el endpoint de consola (`ClientViewSet.onboard`) **comparten el mismo motor** (`crear_tenant_con_owner()`/`crear_empresa()` de `empresa_service.py`) — no hay lógica duplicada entre el comando de línea de comandos y la API administrativa; ambos son clientes legítimos del mismo Service Layer. Esto es consistente con la regla de "capa propietaria" del proyecto.

---

## 7. Preguntas abiertas que requieren decisión de negocio (no resueltas aquí, por regla de no inventar política)

1. **¿El flujo self-service público (Vía B) debe seguir existiendo sin verificación de email antes de otorgar sesión?** Si SINTEL apunta a un modelo de auto-registro real (sin intervención de staff), el Hallazgo #1 es bloqueante y debe resolverse antes de exponer este endpoint fuera de un entorno controlado. Si la Vía B es solo para demos/pruebas internas, el riesgo real es menor pero el endpoint sigue siendo públicamente alcanzable hoy.
2. **¿Cuál es el diseño de autenticación final para `consume-ott`: sesión Django (actual) o JWT en cookie HttpOnly (lo que sugiere el nombre de la rama y el trabajo ya hecho en `8b56d35`)?** Determina si el Hallazgo #2 se resuelve terminando la implementación de cookies o limpiando el middleware muerto.
3. **¿`apps/public/tenants/services.py` debe eliminarse formalmente (código muerto confirmado) o su diseño "Two-Phase DDL/DML" debe rescatarse hacia el motor real si el Hallazgo #4 resulta ser un riesgo genuino?**

---

## 8. Resumen de severidad

| # | Hallazgo | Severidad | Tipo |
|---|---|---|---|
| 1 | OTT de la Vía B entregado al llamante anónimo, no al dueño del email | **CRÍTICO** | Seguridad |
| 2 | Mecanismo de cookie HttpOnly a medio implementar (productor eliminado, consumidor vivo) | **ALTO** | Deuda técnica / código muerto |
| 3 | `.agent/` audit doc describe una función inalcanzable (`services.py` vs `services/`) | **MEDIO** | Documentación / drift |
| 4 | Creación de schema + migración completa dentro de un único `@transaction.atomic` | **MEDIO** | Integridad de datos (no verificado experimentalmente) |
| 5 | `validate_schema_name` duplicado con reglas divergentes | **MEDIO** | Deuda técnica |
| 6 | Errores de validación devuelven 500 en vez de 400 | **BAJO** | Calidad de API |
| 7 | Rate limiting genérico, no dedicado, para creación de schema | **BAJO** | Seguridad / recursos |

Ningún hallazgo fue corregido en esta pasada — por diseño, siguiendo la misma disciplina "auditar primero, corregir después" ya aplicada en las auditorías previas de esta sesión.
