# APP_core_AUDIT — Auditoria integral

**App:** `apps/tenant/core/` (1/16, orden de la mision)
**Fecha:** 2026-08-20
**Commit de cierre:** `57ac7ae` (fix(core): auditoria integral -- codigo
muerto + hardening de seguridad)

---

## FASE A — Inventario funcional

`core` NO es una app de dominio de negocio (no vende, no factura, no
paga nomina). Es la **infraestructura compartida** que el resto de las
16 apps consume:

- **SSoT multitenant:** `SintelTenantBaseModel`/`SedeAwareModel`
  (`models.py`) -- los modelos abstractos que TODA app tenant hereda
  para garantizar aislamiento por `empresa` (obligatorio) y
  `sede`/`area` (opt-in).
- **Contexto Organizacional (OCF/OSF):** 7 servicios
  (`organizational_*.py`) que implementan, en fases documentadas via
  ADR-003/ADR-004, la resolucion de `empresa -> sede -> area`, DSV
  extendido, permisos jerarquicos, y filtros reutilizables para que
  las apps que adoptan `SedeAwareModel` no reimplementen la logica.
- **Middleware de excepciones:** `SintelExceptionMiddleware` --
  captura toda excepcion no manejada, responde JSON estandarizado en
  `/api/`, delega al handler de Django en el resto.
- **Gateway `_apps/`:** `api/urls.py` expone un router de composicion
  hacia las demas apps (`_apps/empresa/`, `_apps/facturas/`,
  `_apps/contabilidad/`, etc.) y el endpoint universal de documentos
  (`/api/v1/core/_apps/facturas/upload-document/`, protegido por
  `FEATURE_UPLOAD_DOCUMENT_ENDPOINT`).
- **Workspace UI:** shell SPA (`workspace.html`, navegacion por anclas
  `#modulo` + `data-tab`) que orquesta el frontend de todas las apps.

**Consumidores:** las 16 apps tenant (heredan `SintelTenantBaseModel`
o `SedeAwareModel`; varias adoptan `OrganizationalContextMixin`).
**Dependencias de `core`:** `empresa` (FK obligatoria en el modelo
base), `perfil` (`TenantProfile` para resolucion de rol/contexto).

---

## FASE B — Modelos

2 modelos, **ambos abstractos** (`Meta.abstract = True`), 0
migraciones propias -- correcto por diseño, no es una omision:
- `SintelTenantBaseModel`: `empresa` FK (PROTECT, obligatoria),
  `created_at`/`updated_at`. `save()` sobrescrito para rechazar
  `empresa_id` nulo incluso si algun caller lo intenta forzar
  (defensa en profundidad).
- `SedeAwareModel(SintelTenantBaseModel)`: agrega `sede`
  (FK PROTECT, `null=True` a nivel BD durante migracion controlada,
  `blank=False` a nivel de formulario) y `area` (FK SET_NULL,
  opcional). Documentado como **opt-in deliberado** (ADR-003) para no
  forzar una migracion simultanea en las 17 apps tenant.
- Advertencia documentada en el propio `Meta` (verificada
  empiricamente en una fase anterior): Django NO fusiona
  `Meta.indexes` de esta clase abstracta con el `Meta.indexes` propio
  de la subclase concreta si esta ultima declara el suyo -- cada app
  que adopte `SedeAwareModel` debe repetir
  `models.Index(fields=['empresa', 'sede'])` explicitamente. Riesgo
  real de indice faltante silencioso; **a verificar por app** en las
  auditorias siguientes que adopten `SedeAwareModel` (confirmado
  hasta ahora: `compras.OrdenCompra`, piloto).

**Hallazgo:** ninguno nuevo. Diseño correcto y ya documentado.

---

## FASE C/D — Logica de negocio y servicios

26 archivos en `services/`. Clasificacion:

| Grupo | Archivos | Rol |
|---|---|---|
| SSoT nuevo (v3.5) | `selectors.py`, `api_mixins.py` | Service Layer modular actual |
| Legacy mantenido | `activation_service.py`, `auth_service.py`, `orchestration.py`, `password_reset.py` | Expuestos en `services/__init__.py`, con consumidores reales verificados |
| Snapshot bridges (activos) | `contabilidad.py`, `empresa.py`, `facturas.py`, `perfil.py`, `landing.py`, `dashboard.py`, `sede_context.py`, `membership.py` | Consumidos por `api/viewsets.py` |
| OCF/OSF (Contexto Organizacional) | `organizational_bridges.py`, `organizational_context.py`, `organizational_dsv.py`, `organizational_filters.py`, `organizational_permissions.py`, `organizational_scope.py`, `organizational_service_layer.py` | 7 archivos, cada uno documentado como una **fase distinta** de 2 proyectos con ADR propio (OCF: ADR-004; OSF: `ORGANIZATIONAL_SCOPE_MASTER_PLAN.md`). **Revisados y descartados como duplicacion** -- responsabilidades genuinamente distintas (bridging cross-app, resolucion de contexto, DSV extendido, filtros reutilizables, jerarquia de permisos, scope, integracion service-layer). Clasificacion FASE L: `DOMAIN_SPECIFIC`, no consolidar. |
| **Muertos (eliminados esta pasada)** | ~~`contabilidad_adapter.py`~~, ~~`empresa_adapter.py`~~, ~~`facturas_maildigester_adapter.py`~~, ~~`landing_adapter.py`~~, ~~`perfil_adapter.py`~~ | Ver FASE K. |

**Hallazgo P2 (dead code, corregido):** ver FASE K.

---

## FASE E/F — Base de datos / ORM

`core` no tiene modelos concretos propios (FASE B) -- no hay queries
directas de "listado" que auditar en este nivel. Los servicios
`organizational_*` SI ejecutan queries sobre modelos de OTRAS apps
(via `SedeAwareModel`); esa auditoria de N+1/`select_related` se
difiere a cada app consumidora (donde el query realmente se ejecuta
en un `get_queryset()`/selector concreto), consistente con que `core`
es una capa de composicion, no de persistencia. **DEFERRED** — sin
riesgo inmediato identificado, sin evidencia de N+1 en esta pasada;
revisar puntualmente si una app auditada mas adelante muestra un
patron N+1 que se origina en una llamada a `organizational_*`.

---

## FASE G — API

`api/urls.py` (271 lineas) expone: router de ViewSets propios
(`CoreLinksViewSet`, `DashboardSectionsViewSet`, `CoreAuthViewSet`,
`TenantInfoView`) + gateway `_apps/<app>/` hacia 12+ apps. Excepciones
a `BaseTenantViewSet`/`lookup_field='uuid'` ya auditadas y confirmadas
legitimas en `documentacion/AUDITORIA_CODIGO_MUERTO_EKG_2026-08-05.md`
(re-verificado en esta pasada, sin cambios desde entonces): 4 casos
son endpoints de composicion sin modelo propio ni ruta de detalle
(`TenantInfoView` publico, `CoreAuthViewSet` session-only,
`CoreLinksViewSet`/`DashboardSectionsViewSet` agregadores), excepciones
documentadas en AGENTS.md §15.1.

**Hallazgo (heredado de F33.15-B Nivel 3, re-confirmado):** el
endpoint universal de documentos vive en
`/api/v1/core/_apps/facturas/upload-document/`, protegido por
`settings.FEATURE_UPLOAD_DOCUMENT_ENDPOINT` (default `False`). El
endpoint legacy equivalente por-app (`factura-upload-ubl`) sigue
`DEPRECATED` en su propio docstring. Sin accion nueva -- ya
documentado y con tests que cubren ambos caminos.

---

## FASE H — Multitenant / Empresa / Sede / Area

`core` **es** el framework que implementa este aislamiento para el
resto de las apps (FASE B). Verificacion cruzada:
- `empresa`: obligatoria, `on_delete=PROTECT`, sin bypass posible
  (`save()` rechaza `empresa_id` nulo).
- `sede`/`area`: opt-in via `SedeAwareModel`, con el DSV extendido en
  `organizational_dsv.py` (empresa -> sede -> area -> modelo).
- Aislamiento cross-tenant: delegado a `django-tenants` (schema por
  tenant) + `TenantSecurityAndURLConfMiddleware` (`apps/public/`) --
  fuera del alcance de `core` en si, pero `core` consume su resultado
  (`request.tenant`) en `SintelExceptionMiddleware` para logging
  contextual.

**Hallazgo:** ninguno nuevo. Framework correcto, ya probado
extensivamente en F33.15-B Nivel 3 (92 tests, incluye
`test_architecture_ssot.py`, `test_organizational_*.py`).

---

## FASE I — Seguridad y permisos

**Hallazgo P0 (seguridad, corregido esta pasada):**
`SintelExceptionMiddleware.process_exception()` incluia el traceback
completo (`error_traceback`) en la respuesta JSON al cliente cuando
`settings.DEBUG=True`. Corregido: el traceback **nunca** se envia al
cliente (solo queda en el log del servidor via `logger.error(...)`,
linea 54-63, que no se toco). Un despliegue con `DEBUG=True` expuesto
por error a una red publica ya no puede filtrar rutas de servidor,
nombres de modulos internos, o estructura del codigo via las
respuestas de error de la API. Commiteado en `57ac7ae`.

Permisos: `core` no define sus propias clases de permisos duplicadas
-- consume `apps.tenant.api.permissions` (regla CLAUDE.md ya
verificada en toda la sesion anterior). `IsTenantAdminOrReadOnly`
(usado por multiples ViewSets de otras apps) resuelve el rol via
`TenantProfile.rol` (schema tenant), hallazgo ya documentado
extensivamente en F33.15-B Nivel 3 -- sin cambios nuevos aqui.

---

## FASE J — Frontend

**Hallazgo P3 (limpieza, corregido esta pasada):**
`static/tenant/core/dashboard/index.html` cargaba 3 `<script>`
apuntando a `/static/core/js/dashboard/*.js`, una ruta que **no
existe en el filesystem** (verificado con `ls`) -- 404 silencioso en
cada carga de pagina. Los mismos assets ya se cargan correctamente
desde `dashboard/templates/tenant/dashboard/partials/
assets_dashboard.html` (app `dashboard`, no `core`). El guard
`typeof window.initDashboardPage === 'function'` en el script inline
siguiente ya degradaba con seguridad ante el 404, por lo que la
correccion es limpieza sin cambio de comportamiento observable.
Commiteado en `57ac7ae`.

`workspace.html` (shell SPA, 18 archivos JS/22 templates en total para
`core`) no se re-audito linea por linea en esta pasada mas alla de lo
ya cubierto por F33.15-B Nivel 3 (migracion FASE 5-BIS confirmada:
navegacion por anclas, sin duplicacion de CDN/scripts en los tests que
siguen activos). **DEFERRED** -- sin evidencia de problema nuevo, no
se re-abre sin señal concreta.

---

## FASE K — Codigo muerto

**Hallazgo P2 (corregido esta pasada):** 5 archivos completos en
`services/` sin ningun consumidor (grep repo-wide de nombres de
funcion y de modulo, 0 hits fuera del propio archivo; EKG offline sin
nodo indexado; `api/viewsets.py` importa los modulos hermanos SIN
sufijo `_adapter` que los reemplazaron; 0 tests que los ejerciten):

| Archivo | Lineas | Reemplazado por |
|---|---|---|
| `contabilidad_adapter.py` | 307 | `services/contabilidad.py` |
| `empresa_adapter.py` | 184 | `services/empresa.py` |
| `facturas_maildigester_adapter.py` | 497 | (sin reemplazo directo identificado; funcionalidad de ingesta de correo vive hoy en `apps/tenant/facturas/services/services_mail_ingestion.py`) |
| `landing_adapter.py` | 125 | `services/landing.py` |
| `perfil_adapter.py` | 158 | `services/perfil.py` |

**Total: 1271 lineas eliminadas.** Databan de la migracion inicial del
proyecto (commit `9d8c94a`, v2.60) y nunca se tocaron desde un cleanup
de "sprint4" (`c1d5658`). Una auditoria previa
(`AUDITORIA_CODIGO_MUERTO_EKG_2026-08-05.md`) ya habia detectado 1
funcion muerta (`core_list_mail_runs()`) dentro de
`facturas_maildigester_adapter.py` sin resolverla (limitacion del EKG,
que no modela funciones sueltas) -- esta pasada confirma que el
archivo completo, y sus 4 hermanos, estan muertos. Verificado:
`manage.py check` + import directo de
`core.services`/`api.viewsets`/`views`/`views_ui`/`urls_ui`, todos
OK. Commiteado en `57ac7ae`.

---

## FASE L — Redundancia y duplicacion

Revisados los 7 archivos `organizational_*.py` (ver FASE C/D) --
**clasificados `DOMAIN_SPECIFIC`, no duplicados**: cada uno documenta
una fase distinta de 2 proyectos arquitectonicos con ADR propio, sin
solapamiento de responsabilidad verificado por lectura directa de
cada docstring + primeras funciones.

Sin otros hallazgos de duplicacion exacta/semantica en esta pasada.

---

## FASE M — Normativa colombiana

**NO_APLICA.** `core` es infraestructura compartida (multitenant,
contexto organizacional, middleware, gateway de composicion) -- no
genera, transmite, ni almacena directamente documentos con
obligaciones tributarias/laborales propias (facturacion, nomina,
retenciones). Las apps que si tienen obligaciones normativas directas
(`facturas`, `contabilidad`, `empleados`, `gastos`, `compras`,
`proveedores`) se auditan en su propio turno con matriz normativa
dedicada, per la mision.

---

## FASE N/O/P/Q — Tests

- **Estado heredado (F33.15-B Nivel 3, verificado exhaustivamente):**
  73 passed, 19 skipped documentados (endpoint universal de
  documentos, workspace UI post-FASE 5-BIS), 0 failed. Ver
  `documentacion/F33.15_TESTING_EXECUTION_STATUS.md`.
- **Regresion post-cambios de esta auditoria:** relanzada tras
  eliminar los 5 archivos muertos + los 2 fixes de frontend/seguridad
  (ningun test referenciaba estos archivos, confirmado en FASE K/I/J,
  por lo que no se esperan fallos nuevos). Corrida en background
  (`apps/tenant/core/`, 92 tests) -- **resultado pendiente al momento
  de cerrar este documento**, se actualiza en
  `APP_AUDIT_MASTER_STATUS.md` cuando termine.
- Reutilizacion de cobertura existente (regla de la mision: no crear
  tests por crear) -- no se identifico ninguna brecha funcional real
  sin cobertura equivalente en esta pasada.

---

## FASE R — Performance

No se midio queries/request de forma sistematica en esta pasada
(`core` no expone endpoints de listado propios sobre modelos
concretos -- FASE E/F). **DEFERRED**, sin riesgo identificado.

---

## FASE S/T — Simplificacion y modernizacion

- Eliminados 1271 lineas de codigo muerto (FASE K) -- reduccion neta
  real, sin abstraccion nueva introducida.
- No se identifico necesidad de nueva abstraccion (`UniversalService`,
  etc.) -- explicitamente evitado per regla de la mision.
- Stack ya moderno donde aplica (Service Layer v3.5, HTMX, sin
  Tabulator en los templates activos de `core`).

---

## Deuda diferida (DEFERRED)

| Item | Razon | Riesgo | Impacto | Recomendacion | Prioridad |
|---|---|---|---|---|---|
| `Meta.indexes` no se fusiona en subclases de `SedeAwareModel` | Limitacion de Django, ya documentada en el propio codigo | Indice `['empresa','sede']` ausente si una app olvida repetirlo | Medio (performance en queries filtradas por sede) | Verificar explicitamente en cada app que adopte `SedeAwareModel` durante su propia auditoria | P2 |
| N+1 en llamadas a `organizational_*` desde apps consumidoras | Query real ocurre en la app consumidora, no en `core` | Desconocido sin medicion | Bajo-Medio | Medir en la auditoria de cada app que use `OrganizationalContextMixin` | P2 |
| `workspace.html`/JS no re-auditado linea por linea mas alla de F33.15-B | Cobertura reciente y verificada ya existe | Bajo | Bajo | Reabrir solo si aparece evidencia concreta nueva | P3 |
| `facturas_maildigester_adapter.py` (eliminado) no tenia reemplazo 1:1 confirmado -- se asume que `apps/tenant/facturas/services/services_mail_ingestion.py` cubre la funcionalidad real de ingesta de correo | Verificacion indirecta (no se leyo linea por linea la equivalencia funcional) | Bajo (el archivo eliminado no tenia consumidores de todas formas) | Ninguno (no hay funcionalidad viva que dependiera del archivo eliminado) | Ninguna accion necesaria; nota informativa | P3 |

---

## FASE X — Release Gate

- [x] business logic audited
- [x] models audited
- [x] services audited (26 archivos, 5 muertos eliminados, 7 OCF/OSF confirmados no-duplicados)
- [ ] ORM/database access audited (DEFERRED, sin modelos concretos propios)
- [x] API audited (re-confirmado, sin cambios desde auditoria previa)
- [x] permissions audited
- [x] tenant isolation tested (heredado F33.15-B, 92 tests)
- [x] empresa scope tested
- [x] sede scope tested (framework propio de `core`, mixin opt-in)
- [x] area scope tested
- [x] frontend audited
- [x] dead code classified (5 archivos DEAD_CONFIRMED, eliminados)
- [x] duplication classified (7 archivos DOMAIN_SPECIFIC, no duplicados)
- [ ] unnecessary DB calls reviewed (DEFERRED)
- [x] normative matrix reviewed (NO_APLICA, justificado)
- [x] tests unified (cobertura existente reutilizada, sin gaps identificados)
- [ ] regression PASS (**pendiente confirmacion del run en background**)
- [x] governance PASS (`manage.py check` limpio)
- [x] impact analysis (grep repo-wide + EKG offline + imports directos)
- [x] documentation updated (este documento + `APP_AUDIT_MASTER_STATUS.md`)

## FASE Y — Decision final

**COMPLETED_WITH_DEFERRED** (pendiente de confirmar como `COMPLETED`
en cuanto el run de regresion en background termine sin fallos --
ver `APP_AUDIT_MASTER_STATUS.md` para el resultado final). 4 items
diferidos documentados arriba, ninguno P0/P1.
