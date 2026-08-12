# FASE 29 -- Auditoria de reverse()/reverse_lazy()/resolve()/redirect()

Auditoria de solo lectura (sin ediciones, sin pytest) de todos los usos de
`reverse(`, `reverse_lazy(`, `resolve(` y `redirect(` en `apps/`, `config/`,
`tests/` y `scripts/`. Metodo: para cada call site se identifico el nombre de
URL referenciado y se contrasto contra el registro real en
`config/urls_public.py`, `config/urls_tenant.py`, `config/urls.py` (LEGACY,
ver mas abajo) y los `urls.py` / `urls_ui.py` / `api/urls.py` incluidos,
verificando `app_name` de cada modulo incluido y si el `include()` pasa
`namespace=` explicito (mismo metodo que resolvio el caso `workspace` de
F27/F28). Para las llamadas con `args=`/`kwargs=` se verifico
`lookup_field`/`lookup_url_kwarg` del ViewSet real referenciado.

**[Actualización post-auditoría]** Este documento es un snapshot de
investigación de solo lectura, tal como se generó. Los hallazgos #1
(WRONG_LOOKUP, 16 sites) y #2 (LEGACY `admin-tenants-*`, 37 sites) **ya
fueron corregidos** en la misma sesión de F29 — ver
`documentacion/F29_FINDINGS.md` F29-001/F29-005 para el detalle de la
corrección real aplicada. Los hallazgos #3 (`tenant_dashboard:index`) y #4
(colisión `user-list`/`user-detail`) siguen sin corregir, documentados en
`F29_FINDINGS.md` F29-006/F29-007.

## NUEVOS HALLAZGOS ACCIONABLES (no reportados/corregidos en F27/F28)

### 1. WRONG_LOOKUP nuevo -- `kwargs={"pk": ...}` contra ViewSets con `lookup_field="uuid"`

Mismo patron de bug que el ya corregido en `test_factura_detail_anexos_api.py`,
`test_facturas_list_detail_payloads.py` y `test_import_ubl_heavy_payload.py`,
pero **sin corregir** en estos 5 archivos (16 call sites). `FacturaViewSet`,
`AsientoContableViewSet` y `CuentaContableViewSet` no sobreescriben
`lookup_field`/`lookup_url_kwarg`, por lo que heredan de `BaseTenantViewSet`
(`apps/tenant/api/base.py:48-49`): `lookup_field = "uuid"`,
`lookup_url_kwarg = "uuid"`. El router DRF genera el grupo nombrado `uuid` en
la URL, no `pk` -- `reverse(..., kwargs={"pk": ...})` debe fallar con
`NoReverseMatch`.

| File:line | Nombre referenciado | Real requerido | Verdict |
|---|---|---|---|
| tests/tenant/security/test_norma_exposicion_datos.py:101 | `factura-detail` kwargs `{"pk": factura.id}` | kwargs `{"uuid": factura.uuid}` | WRONG_LOOKUP |
| tests/tenant/security/test_norma_exposicion_datos.py:151 | `factura-detail` kwargs `{"pk": ...}` | uuid | WRONG_LOOKUP |
| tests/tenant/security/test_norma_exposicion_datos.py:158 | `factura-xml` kwargs `{"pk": ...}` | uuid | WRONG_LOOKUP |
| tests/tenant/security/test_norma_exposicion_datos.py:203 | `asiento-contable-detail` kwargs `{"pk": asiento.id}` | uuid (hereda BaseTenantViewSet) | WRONG_LOOKUP |
| tests/tenant/security/test_norma_exposicion_datos.py:252 | `cuenta-contable-detail` kwargs `{"pk": cuenta.id}` | uuid (hereda BaseTenantViewSet) | WRONG_LOOKUP |
| tests/tenant/facturas/test_factura_immutability.py:94 | `factura-detail` kwargs `{"pk": ...}` | uuid | WRONG_LOOKUP |
| tests/tenant/facturas/test_factura_immutability.py:127 | idem | uuid | WRONG_LOOKUP |
| tests/tenant/facturas/test_factura_immutability.py:159 | idem | uuid | WRONG_LOOKUP |
| tests/tenant/facturas/test_factura_immutability.py:189 | idem | uuid | WRONG_LOOKUP |
| tests/tenant/facturas/test_factura_immutability.py:221 | idem | uuid | WRONG_LOOKUP |
| tests/tenant/facturas/test_factura_immutability.py:254 | idem | uuid | WRONG_LOOKUP |
| tests/tenant/facturas/test_factura_immutability.py:320 | `factura-xml` kwargs `{"pk": ...}` | uuid | WRONG_LOOKUP |
| tests/tenant/facturas/test_facturas_api.py:164 | `factura-detail` kwargs `{"pk": factura.pk}` | uuid | WRONG_LOOKUP |
| tests/tenant/facturas/test_api_facturas_forensics.py:113 | `factura-detail` kwargs `{"pk": fact_id}` | uuid | WRONG_LOOKUP |
| tests/tenant/facturas/test_api_e2e.py:145 | `factura-detail` kwargs `{"pk": factura.id}` | uuid | WRONG_LOOKUP |
| tests/tenant/facturas/test_api_e2e.py:177 | `factura-detail` kwargs `{"pk": factura.id}` | uuid | WRONG_LOOKUP |

Nota: en el mismo archivo `test_norma_exposicion_datos.py:283`,
`reverse("empresa-detail", kwargs={"pk": self.empresa.id})` es **CORRECT**:
`EmpresaViewSet` hereda directo de `viewsets.ModelViewSet` (no de
`BaseTenantViewSet`), asi que su lookup por defecto es `pk`.

### 2. LEGACY nuevo -- cluster `admin-tenants-*` / `admin-tenant-domains-*` / `admin-dt-tenants`

37 call sites en 7 archivos referencian nombres que **nunca resuelven** contra
el URLConf actual. Evidencia de que son legado (definicion de LEGACY:
"nombre que existio, evidencia en git/comentarios"): el propio comentario en
`tests/public/tenants/test_admin_api_crud_tenants.py:20,64` dice
`# router basename="admin-tenants"`, pero el router real
(`apps/public/tenants/api/urls.py` + `VIEWSETS` en
`apps/public/tenants/api/viewsets.py:671`) usa `basename="tenant"` (Client) y
`basename="domain"` (Domain) desde el refactor "Fase 5-BIS" (commit
`60d8a33`, migracion a django-tables2 / rebrand). Los nombres reales son:
`tenant-list`, `tenant-detail`, `tenant-onboard` (accion `url_name="onboard"`),
`tenant-toggle-active`, `domain-list`, `domain-detail`; el DataTables de
tenants ahora vive en `apps/public/console/api/urls.py`
(`app_name="console_api"`, incluido con `namespace='console_api'`) como
`console_api:dt_tenants` -- no `admin-dt-tenants`.

Contraste util: `tests/public/tenants/test_onboard_resilience.py` SI usa el
nombre correcto `reverse("tenant-onboard")` (CORRECT) -- confirma que el
nombre real es `tenant-onboard`, no `admin-tenants-onboard`.

| File | Sites | Nombres usados | Real |
|---|---|---|---|
| tests/public/tenants/test_admin_api_crud_tenants.py | 20, 40, 62-64, 95 (4) | `admin-tenants-list/detail/onboard` | `tenant-list/detail/onboard` |
| tests/public/tenants/test_api.py | 26,46,71,91,101,121,142,161,182,195 (10) | `admin-tenants-list/detail`, `admin-tenant-domains-list/detail` | `tenant-list/detail`, `domain-list/detail` |
| tests/public/tenants/test_tenant_suspension.py | 296,340,387,428,497 (5) | `admin-tenants-toggle-status` | `tenant-toggle-active` |
| tests/public/tenants/test_domain_normalization.py | 63,129,189,273,321,355,398,446,494 (9) | `admin-tenants-onboard` | `tenant-onboard` |
| tests/public/tenants/test_onboard.py | 29,75,85 (3) | `admin-tenants-onboard` | `tenant-onboard` |
| tests/public/tenants/test_datatables_tenants.py | 30,59,72 (3) | `admin-dt-tenants` | `console_api:dt_tenants` |
| tests/public/tenants/test_datatables_domain_validation.py | 55,134,191 (3) | `admin-dt-tenants` | `console_api:dt_tenants` |

Classification: **LEGACY** (37 sites total) -- codigo/tests que asumen un
esquema de rutas anterior al refactor de Fase 5-BIS. Si estos tests corren
hoy, fallan con `NoReverseMatch` en la primera linea `reverse(...)`.

### 3. LEGACY nuevo -- `tenant_dashboard:index` nunca registrado

`apps/tenant/dashboard/urls.py` declara `app_name = 'tenant_dashboard'` pero
tiene `urlpatterns = []` y un comentario explicito: *"Este archivo se
mantiene vacio... No debe ser incluido en config/urls_tenant.py"*. En efecto,
no esta incluido en ningun URLConf vivo (`config/urls_tenant.py`,
`config/urls_public.py`). Dos tests llaman `reverse("tenant_dashboard:index")`
directamente (no en un helper condicional) y fallarian con `NoReverseMatch`:

| File:line | Verdict |
|---|---|
| tests/general/test_system_health.py:207 | LEGACY |
| tests/tenant/landing/test_private_routing.py:71 | LEGACY |

### 4. Hallazgo adicional (fuera de la taxonomia estricta) -- colision de nombre `user-list`/`user-detail`

`apps/public/accounts/api/public_urls.py` registra `PublicUserViewSet` con
`basename="user"` y se incluye sin namespace en
`path('api/public/v1/', include('config.public_api_urls'))`
(`config/urls_public.py:95`). Por separado,
`apps/public/accounts/api/urls.py` registra `UserAdminViewSet` con el
**mismo** `basename="user"` (`apps/public/accounts/api/viewsets.py:171`) y se
incluye tambien sin namespace en
`path('api/admin/v1/accounts/', include('apps.public.accounts.api.urls'))`
(`config/urls_public.py:104`). Ambos includes cuelgan del mismo URLConf plano
(`urls_public.py`), asi que `user-list`/`user-detail` quedan registrados dos
veces bajo el mismo nombre en namespaces distintos de path (`/api/public/v1/`
vs `/api/admin/v1/accounts/`). Como `api/public/v1/` se registra primero en
`urlpatterns`, `reverse("user-list")`/`reverse("user-detail")` resuelve
consistentemente al endpoint PUBLICO (`/api/public/v1/users/...`), no al
endpoint ADMIN que los tests parecen querer ejercitar.

Afectados: `tests/public/accounts/test_admin_users_list.py` (5 sites) y
`tests/public/accounts/test_user_crud_api.py` (11 sites) -- ambos usan
`reverse("user-list")` / `reverse("user-detail")` para probar el CRUD admin
de usuarios via `/api/admin/v1/accounts/`, pero technicamente obtienen la URL
del endpoint publico de registro (`PublicUserViewSet`). No se puede clasificar
limpiamente en la taxonomia dada (no es namespace faltante, no es pk/uuid);
se reporta aparte como **posible ambiguedad de nombre / bug silencioso**: si
ambos ViewSets exponen list/create de forma superficialmente compatible el
test puede "pasar" ejercitando el endpoint equivocado.

---

## 1. Totales de call sites

Metodologia: `\breverse\(`, `reverse_lazy\(`, `\bredirect\(`, `resolve\(`
sobre archivos `*.py`, excluyendo `.venv`, `node_modules`, `__pycache__`,
migraciones. Se excluyeron manualmente los falsos positivos que no son
Django URL routing: `OrganizationalScope.resolve()` /
`OrganizationalContext.resolve()` (servicio interno, no relacionado a URLs),
`Path(...).resolve()` (stdlib), y menciones en docstrings/comentarios.

| Funcion | Total | apps/ (incl. apps/*/tests) | tests/ (top-level) | config/ | scripts/ (informativo) |
|---|---|---|---|---|---|
| `reverse(` | 331 | 67 | 256 | 1 | 7 |
| `reverse_lazy(` | 0 | 0 | 0 | 0 | 0 |
| `redirect(` | 20 | 13 | 0 | 7 | 0 |
| `resolve(` (Django URL, real) | ~2 | 0 | 1 | 0 | ~4 (diagnostico, imports incluidos) |

`redirect()` no aparece nunca en `tests/`: los tests verifican redirecciones
via `response.url == reverse(...)` / status 302, no llaman `redirect()`
directamente. `reverse_lazy()` no se usa en ningun lugar del repo.

## 2. Tabla de call sites NO clasificados como CORRECT

(Ademas de los 4 clusters nuevos detallados arriba, que se repiten aqui de
forma resumida por completitud de la tabla.)

| File:line | Nombre referenciado | Real registrado | Verdict |
|---|---|---|---|
| tests/tenant/security/test_norma_exposicion_datos.py:101,151,158,203,252 | `factura-detail`/`factura-xml`/`asiento-contable-detail`/`cuenta-contable-detail` con kwargs `pk` | uuid | WRONG_LOOKUP (5) |
| tests/tenant/facturas/test_factura_immutability.py:94,127,159,189,221,254,320 | `factura-detail`/`factura-xml` kwargs `pk` | uuid | WRONG_LOOKUP (7) |
| tests/tenant/facturas/test_facturas_api.py:164 | `factura-detail` kwargs `pk` | uuid | WRONG_LOOKUP (1) |
| tests/tenant/facturas/test_api_facturas_forensics.py:113 | `factura-detail` kwargs `pk` | uuid | WRONG_LOOKUP (1) |
| tests/tenant/facturas/test_api_e2e.py:145,177 | `factura-detail` kwargs `pk` | uuid | WRONG_LOOKUP (2) |
| tests/public/tenants/test_admin_api_crud_tenants.py:20,40,62,95 | `admin-tenants-*` | `tenant-*` | LEGACY (4) |
| tests/public/tenants/test_api.py:26,46,71,91,101,121,142,161,182,195 | `admin-tenants-*`, `admin-tenant-domains-*` | `tenant-*`, `domain-*` | LEGACY (10) |
| tests/public/tenants/test_tenant_suspension.py:296,340,387,428,497 | `admin-tenants-toggle-status` | `tenant-toggle-active` | LEGACY (5) |
| tests/public/tenants/test_domain_normalization.py:63,129,189,273,321,355,398,446,494 | `admin-tenants-onboard` | `tenant-onboard` | LEGACY (9) |
| tests/public/tenants/test_onboard.py:29,75,85 | `admin-tenants-onboard` | `tenant-onboard` | LEGACY (3) |
| tests/public/tenants/test_datatables_tenants.py:30,59,72 | `admin-dt-tenants` | `console_api:dt_tenants` | LEGACY (3) |
| tests/public/tenants/test_datatables_domain_validation.py:55,134,191 | `admin-dt-tenants` | `console_api:dt_tenants` | LEGACY (3) |
| tests/general/test_system_health.py:207 | `tenant_dashboard:index` | (no registrado, urlpatterns vacio) | LEGACY (1) |
| tests/tenant/landing/test_private_routing.py:71 | `tenant_dashboard:index` | (no registrado) | LEGACY (1) |
| config/urls.py:48 | `console:dashboard` dentro de `root_view` | nombre valido, pero `config/urls.py` NO es `ROOT_URLCONF`/`TENANT_URLCONF` (settings usa `config.urls_public` / `config.urls_tenant`) | LEGACY (1, codigo muerto/inalcanzable) |
| tests/public/accounts/test_admin_users_list.py (5), test_user_crud_api.py (11) | `user-list`/`user-detail` | registrado 2 veces (basename `user` colisiona entre `public_urls.py` y `accounts/api/urls.py`); gana el registrado primero (`/api/public/v1/`) | Fuera de taxonomia -- posible endpoint equivocado (ver seccion 4 arriba) |
| tests/public/tenants/test_api_crud_tenants_dynamic.py:50,90 | `f"{basename}-list"` / `f"{basename}-detail"` (basename derivado en runtime desde `VIEWSETS`) | se auto-verifica contra el registro real | UNVERIFIED por definicion (dinamico), pero verificado manualmente como CORRECT por construccion |
| tests/public/tenants/test_api_onboard_dynamic.py:40 | `f"{basename}-onboard"` (idem, con skip si no existe) | idem | UNVERIFIED por definicion, CORRECT por construccion (con skip defensivo) |

Ya corregidos en F27/F28 (confirmado CORRECT en el codigo actual, no se
reportan de nuevo): `apps/tenant/core/tests/test_workspace_facturas_links_and_column.py`,
`test_workspace_facturas_modal.py`, `test_workspace_links_strict.py`,
`tests/tenant/core/test_workspace_crud_integration.py` (usan
`core_ui:workspace`); `apps/tenant/facturas/tests/test_factura_detail_anexos_api.py`,
`test_facturas_list_detail_payloads.py`, `test_import_ubl_heavy_payload.py`
(usan `args=[uuid]`).

No se encontraron casos nuevos de `WRONG_ROOT_URLCONF` (los archivos de test
tenant ya migrados a `SintelTenantTestCase` por F27/F28; no se hallaron
nuevos usos de `TenantTestCase` crudo con `reverse()` de por medio en la
muestra revisada) ni `DUPLICATE` en el sentido estricto de copy-paste
redundante evidente.

## 3. Resumen por clasificacion

| Clasificacion | Sites |
|---|---|
| CORRECT | ~290 (mayoria: `args=[...]` posicional, namespaces explicitos correctos, DRF router basenames sin namespace consistentes con include() sin `namespace=`) |
| WRONG_LOOKUP (nuevo) | 16 |
| LEGACY (nuevo, cluster admin-tenants/admin-dt-tenants) | 37 |
| LEGACY (nuevo, tenant_dashboard:index) | 2 |
| LEGACY (nuevo, config/urls.py codigo muerto) | 1 |
| Fuera de taxonomia (colision user-list/user-detail) | 16 (5+11, informativo) |
| UNVERIFIED (dinamico, verificado manualmente OK) | 2 |
| WRONG_NAMESPACE / WRONG_LOOKUP ya corregidos en F27/F28 (confirmado CORRECT hoy) | 7 archivos, no re-flageados |
| WRONG_ROOT_URLCONF nuevo | 0 |
| DUPLICATE estricto | 0 |

**Total call sites auditados: 331 `reverse()` + 20 `redirect()` + ~2
`resolve()` reales (Django) + 0 `reverse_lazy()` = ~353** en `apps/`,
`config/`, `tests/` (mas ~7-11 adicionales en `scripts/`, tratados como
informativos/diagnostico, no parte del suite de tests ni del codigo de
produccion servido).
