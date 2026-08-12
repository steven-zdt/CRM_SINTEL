# F29 — Hallazgos (Contratos URL/UUID + Test Harness)

**Fecha:** 2026-08-11. Continuación directa de F28, que dejó dos hallazgos
reales abiertos (`self.f.id` vs `.uuid`, `reverse("workspace")` sin
resolver). F29 los cerró con evidencia y, en el proceso, auditó **todos**
los usos de `reverse()`/`reverse_lazy()`/`resolve()`/`redirect()` del repo
(~353 call sites), encontrando y corrigiendo clusters adicionales del mismo
tipo de bug.

---

## F29-001 — Contrato UUID: `lookup_field="uuid"` vs `kwargs={"pk": ...}`

**23 call sites corregidos en 8 archivos.** `BaseTenantViewSet` fija
`lookup_field = lookup_url_kwarg = "uuid"` — cualquier `reverse()` con
`args=[obj.id]` o `kwargs={"pk": obj.id}` contra un ViewSet que hereda de
ahí genera una URL que no resuelve al objeto real (404) o, en algunos
casos, ni siquiera reversa (`NoReverseMatch` si el grupo nombrado es
`uuid`, no `pk`).

| Archivo | Sites | Detalle |
|---|---|---|
| `apps/tenant/facturas/tests/test_factura_detail_anexos_api.py` | 5 | `.id`→`.uuid` |
| `apps/tenant/facturas/tests/test_facturas_list_detail_payloads.py` | 1 | `.id`→`.uuid` |
| `apps/tenant/facturas/tests/test_import_ubl_heavy_payload.py` | 1 | `.id`→`.uuid` |
| `tests/tenant/security/test_norma_exposicion_datos.py` | 5 | `.id`→`.uuid`; además `factura-xml`→`factura-xml-ubl` (nombre que nunca existió) y fixture `Factura.xml_content`→`FacturaAnexos.ubl_xml` (F26-003, campo deprecado) |
| `tests/tenant/facturas/test_factura_immutability.py` | 7 | idem (6 `factura-detail` + 1 `factura-xml`→`factura-xml-ubl` con el mismo fix de fixture/shape) |
| `tests/tenant/facturas/test_facturas_api.py` | 1 | `.pk`→`.uuid` |
| `tests/tenant/facturas/test_api_facturas_forensics.py` | 1 | usa `r.json()["uuid"]` de la respuesta de upload en vez de `["id"]` |
| `tests/tenant/facturas/test_api_e2e.py` | 2 | `.id`→`.uuid` |

**Hallazgo compuesto en 2 de los archivos** (`test_norma_exposicion_datos.py`,
`test_factura_immutability.py`): el nombre `factura-xml` (bare) **nunca
existió** — los nombres reales son `factura-xml-ubl` y
`factura-xml-app-response` (`FacturaXMLMixin`,
`apps/tenant/facturas/api/mixins/factura_xml_mixin.py`). Además, la
respuesta exitosa de `factura-xml-ubl` es un `HttpResponse` XML crudo
(`Content-Type: application/xml`), **no JSON** — ambos tests asumían
`resp.json()["xml"]`, un contrato que nunca existió en el código actual.
Corregido con el mismo patrón ya verificado en
`test_factura_detail_anexos_api.py::test_get_ubl_xml` (chequeo de
`Content-Type` + contenido crudo). También corregido el fixture: ambos
tests creaban la factura con `xml_content="..."` (campo deprecado desde
F26, ver `F26_FINDINGS.md` F26-003) en vez de `FacturaAnexos.ubl_xml` (la
SSoT real que `FacturaSelectors.obtener_anexo_xml()` consulta) — sin este
fix, el endpoint real habría respondido 204 (sin contenido), no 200.

**No corregido, confirmado CORRECT:**
`test_norma_exposicion_datos.py:283` (`reverse("empresa-detail", kwargs={"pk":...})`)
es correcto tal cual — `EmpresaViewSet` no hereda `BaseTenantViewSet`
(hereda `viewsets.ModelViewSet` directo), su lookup real es `pk`.

## F29-002 — Contrato URL `workspace`: namespace faltante, no bug de producción

**24 call sites corregidos en 4 archivos** (`apps/tenant/core/tests/test_workspace_facturas_links_and_column.py`,
`test_workspace_facturas_modal.py`, `test_workspace_links_strict.py`,
`tests/tenant/core/test_workspace_crud_integration.py`).

Diagnóstico confirmado caminando el árbol real de `URLResolver`
(`get_resolver('config.urls_tenant')._populate()` + recorrido manual de
`url_patterns`, no solo `reverse_dict`): el patrón `path('workspace/', ...,
name='workspace')` vive en `apps/tenant/core/urls_ui.py`, que declara
`app_name = 'core_ui'` (línea 28). Se incluye en `config/urls_tenant.py`
como `path('', include('apps.tenant.core.urls_ui'))` **sin** `namespace=`
explícito — Django toma automáticamente el `app_name` del módulo incluido
como namespace en ese caso. El nombre reversible real es
**`core_ui:workspace`**, nunca `workspace` a secas ni `tenant-workspace`
(que nunca existió).

**Confirmado que NO es un bug de producción:** `reverse('core_ui:workspace')`
resuelve correctamente a `/workspace/`, y una petición HTTP real a
`/workspace/` responde 302 (redirect a login, comportamiento esperado sin
autenticar) — el routing real, servido por
`TenantMainMiddleware`/`request.urlconf` dinámico, siempre funcionó. El
bug era exclusivamente en cómo los tests invocaban `reverse()`.

**Verificado, no solo corregido:** `test_workspace_page_loads` (el test más
simple del archivo más grande) pasa 100% limpio tras el fix — confirma la
causa raíz.

## F29-003 — Hallazgo nuevo (no corregido): `self.user` propio sin membership en `test_workspace_crud_integration.py`

Tras F29-002, la mayoría de los tests de `test_workspace_crud_integration.py`
siguen fallando, pero por una causa **distinta y no relacionada** con URLs:
sus 3 clases sobreescriben `self.user`/`self.client` en su propio `setUp()`
(`User.objects.create_user(...)` + `force_login`, después de
`super().setUp()`) — esto reemplaza al usuario admin real que
`SintelTenantTestCase` ya provee (con `TenantProfile`/`TenantMembership`)
por uno sin perfil de tenant. Resultado observado: `response.status_code`
sigue siendo 200 pero `response.content` llega vacío en los tests que
verifican HTML — sugiere que algún gate de membership intercepta
silenciosamente. **No investigado a fondo ni corregido** en este pase
(fuera del alcance de "contratos de URL", que era la misión de F29) —
documentado con evidencia para una fase dedicada.

## F29-004 — Auditoría completa de `reverse()`/`redirect()`/`resolve()` (agente dedicado)

Ver `documentacion/F29_URL_REVERSE_AUDIT.md` para el detalle completo.
~353 call sites auditados (331 `reverse()`, 20 `redirect()`, ~2 `resolve()`
reales, 0 `reverse_lazy()`). Resumen:

- **~290 CORRECT** (mayoría).
- **16 WRONG_LOOKUP** nuevos → **corregidos** (ver F29-001, ya contados ahí
  junto con los que se encontraron antes de lanzar la auditoría).
- **37 LEGACY** nuevos (cluster `admin-tenants-*`/`admin-tenant-domains-*`/
  `admin-dt-tenants`) → **corregidos** (ver F29-005 abajo).
- **2 LEGACY** nuevos (`tenant_dashboard:index`) → **NO corregidos**,
  documentados (ver F29-006).
- **1 LEGACY** (código muerto en `config/urls.py`, no es
  `ROOT_URLCONF`/`TENANT_URLCONF`) → **NO corregido**, informativo.
- **16 sites fuera de taxonomía** (colisión de nombre `user-list`/`user-detail`)
  → **NO corregidos**, documentados (ver F29-007).
- **0 WRONG_ROOT_URLCONF nuevos, 0 DUPLICATE estrictos.**

## F29-005 — LEGACY corregido: cluster `admin-tenants-*` (post Fase 5-BIS)

**37 call sites corregidos en 7 archivos.** El router de tenants/dominios
cambió de basename en el refactor "Fase 5-BIS" (commit `60d8a33`,
migración a django-tables2/rebrand) — `apps/public/tenants/api/viewsets.py:671`
usa `basename="tenant"` (antes presumiblemente `"admin-tenants"`, evidencia:
comentario literal `# router basename="admin-tenants"` en
`test_admin_api_crud_tenants.py:20,64`, que nunca se actualizó tras el
refactor). Estos 37 sites referenciaban nombres que **nunca resuelven**
contra el URLConf actual — cualquier test que los ejecutara fallaba con
`NoReverseMatch` en la primera línea.

| Archivo | Sites | Nombre viejo → real |
|---|---|---|
| `tests/public/tenants/test_admin_api_crud_tenants.py` | 4 | `admin-tenants-list/detail/onboard` → `tenant-list/detail/onboard` |
| `tests/public/tenants/test_api.py` | 10 | `admin-tenants-*`, `admin-tenant-domains-*` → `tenant-*`, `domain-*` |
| `tests/public/tenants/test_tenant_suspension.py` | 5 | `admin-tenants-toggle-status` → `tenant-toggle-active` |
| `tests/public/tenants/test_domain_normalization.py` | 9 | `admin-tenants-onboard` → `tenant-onboard` |
| `tests/public/tenants/test_onboard.py` | 3 | `admin-tenants-onboard` → `tenant-onboard` |
| `tests/public/tenants/test_datatables_tenants.py` | 3 | `admin-dt-tenants` → `console_api:dt_tenants` |
| `tests/public/tenants/test_datatables_domain_validation.py` | 3 | `admin-dt-tenants` → `console_api:dt_tenants` |

Cada nombre real se confirmó con evidencia antes de aplicar el cambio (grep
del `@action`/router real, y para el caso `console_api:dt_tenants`,
reproducción directa con `reverse()` vía `manage.py shell`). Contraste que
confirma el patrón: `tests/public/tenants/test_onboard_resilience.py` ya
usaba el nombre correcto `tenant-onboard` — prueba que el nombre real
siempre fue ese, no que cambió recientemente.

## F29-006 — LEGACY no corregido: `tenant_dashboard:index`

`apps/tenant/dashboard/urls.py` declara `app_name = 'tenant_dashboard'` con
`urlpatterns = []` y un comentario explícito: el archivo se mantiene vacío
deliberadamente y no debe incluirse en `config/urls_tenant.py` — y en
efecto no está incluido en ningún URLConf vivo. Dos tests
(`tests/general/test_system_health.py:207`,
`tests/tenant/landing/test_private_routing.py:71`) llaman
`reverse("tenant_dashboard:index")` directamente y fallarían con
`NoReverseMatch`. **No corregido**: a diferencia del cluster admin-tenants
(que tenía un reemplazo real y verificable), aquí no existe ningún
`tenant_dashboard:index` real al que apuntar — corregirlo exige decidir si
ese dashboard alguna vez se va a implementar (y entonces el test documenta
un TODO legítimo) o si el test debe eliminarse/skipearse
(funcionalidad que nunca existió). Decisión de producto, no de testing —
fuera de alcance de F29.

## F29-007 — Hallazgo fuera de taxonomía, no corregido: colisión de nombre `user-list`/`user-detail`

`PublicUserViewSet` (`basename="user"`, público, registro de usuarios) y
`UserAdminViewSet` (`basename="user"`, admin, CRUD de usuarios) están
registrados con el **mismo basename**, ambos sin namespace, en el mismo
`config/urls_public.py`. `reverse("user-list")`/`reverse("user-detail")`
resuelve determinísticamente al primero registrado en `urlpatterns`
(`/api/public/v1/`, el endpoint **público** de registro) — nunca al admin.
16 call sites en `tests/public/accounts/test_admin_users_list.py` (5) y
`test_user_crud_api.py` (11) usan estos nombres asumiendo que apuntan al
endpoint admin. **No corregido**: el fix correcto (agregar `namespace=` a
uno o ambos `include()`) toca `config/urls_public.py` — código de
producción real, no solo tests — y cambiar un namespace de URLs públicas ya
en uso es un cambio de mayor riesgo que requiere su propia validación
dedicada (posibles consumidores externos del nombre actual). Documentado
con evidencia completa, no corregido en este pase.

---

## Resumen

| # | Hallazgo | Sites | Acción |
|---|---|---|---|
| F29-001 | `.id`/`.pk` vs `.uuid` (`lookup_field`) | 23 | **Corregido**, 8 archivos |
| F29-002 | `reverse("workspace")` sin namespace | 24 | **Corregido**, 4 archivos |
| F29-003 | `self.user` propio sin membership | — | Documentado, no corregido |
| F29-004 | Auditoría completa reverse()/redirect() | ~353 | Completada (agente dedicado) |
| F29-005 | Cluster LEGACY `admin-tenants-*` | 37 | **Corregido**, 7 archivos |
| F29-006 | LEGACY `tenant_dashboard:index` | 2 | Documentado, no corregido (decisión de producto) |
| F29-007 | Colisión `user-list`/`user-detail` | 16 | Documentado, no corregido (toca producción) |

**Total: 84 call sites corregidos en 19 archivos de test.** 0 cambios de
código de producción (todos los fixes fueron en tests; el único fix
"de producción" fue en F28: normalización de base class, tampoco
producción real).
