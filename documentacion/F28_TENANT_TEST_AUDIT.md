# FASE 28 -- Auditoria de tests con `TenantTestCase` (raw) vs `SintelTenantTestCase`

Investigacion de solo lectura. No se edito ningun archivo de test, no se corrio pytest, no se
corrieron migraciones.

## 1. Verificacion del listado de 34 archivos (FASE 27)

Se corrio `grep -rn "^from django_tenants\.test\.cases import.*TenantTestCase"` sobre todo el
repo (mas una segunda pasada dirigida a los 2 archivos de `tests/tenant/core/smoke/` que
importan `TenantTestCase` indirectamente desde `apps/tenant/core/tests/base_test.py`, un shim que
re-exporta el `TenantTestCase` crudo de django-tenants -- confirmado leyendo ese archivo).

**Resultado: el listado de 34 archivos de FASE 27 sigue siendo exacto.** Los 34 archivos
efectivamente heredan (directa o indirectamente via el shim) de
`django_tenants.test.cases.TenantTestCase` crudo, y ninguno fue corregido/migrado desde FASE 27.

Se encontraron 3 desviaciones que vale la pena registrar, ninguna afecta el conteo de 34:

- **Drift real (archivo nuevo no capturado por FASE 27):**
  `apps/tenant/dashboard/tests/test_extractores.py:6` hace
  `from django_tenants.test.cases import TenantTestCase as TestCase` y 4 clases heredan de ese
  alias (`FacturasExtractorTestCase`, `InventarioExtractorTestCase`,
  `EmpleadosExtractorTestCase`, `ProveedoresExtractorTestCase`). Este archivo usa `TenantTestCase`
  crudo genuinamente pero **no estaba en el listado de 34** de FASE 27. Se documenta aqui pero
  **no se incluye en la clasificacion ni en el tally** de este pase, ya que el encargo es
  exclusivamente sobre los 34 archivos dados. Recomendado incluirlo en un pase de migracion
  posterior.
- **Falsos candidatos descartados (grep amplio encontro el nombre `TenantTestCase` pero no aplica):**
  - `tests/tenant/security/test_url_isolation.py` y `tests/tenant/core/smoke/test_core_security_routing.py`
    importan `TenantTestCase` crudo pero la clase de test real hereda de `SintelTenantTestCase`
    (import muerto/vestigial). Ya estan migrados, correctamente excluidos del listado de 34.
  - `tests/tenant/security/test_cross_tenant.py` importa `TenantTestCase` crudo (linea 10) pero
    nunca lo usa como base -- son tests con `@pytest.mark.django_db` a nivel de funcion, no de
    clase. Import muerto, correctamente excluido.
  - `apps/config/tests/base_tenant.py` define `TenantAPITestCase(TenantTestCase)`, una base
    class alternativa (no `SintelTenantTestCase`) usada por 15 archivos fuera del listado de 34
    (`apps/tenant/contabilidad/tests/test_retenciones_api.py`, etc.). Fuera de alcance de este
    audit.
  - `apps/public/console/tests.py` usa `TenantTestCase` crudo en 4 clases, pero vive en
    `apps/public/` (fuera del arbol `apps/tenant/*` y `tests/*` que cubre el encargo). No incluido.

## 2. Recordatorio de lo que aporta `SintelTenantTestCase` (`tests/tenant/base_test.py`)

- `setUp()` (linea 111-165) primero llama `super().setUp()` (que ejecuta
  `TenantTestCase.setUp()`, creando/activando el schema del tenant), **luego** hace el fix critico
  de FASE 27: `override_settings(ROOT_URLCONF=settings.TENANT_URLCONF)` + `set_urlconf(...)`
  (lineas 133-136). Este fix vive dentro de `setUp()`, no en `setUpClass()`/`setup_tenant()`.
  **Consecuencia importante para la clasificacion:** si una subclase sobreescribe `setUp()` sin
  llamar `super().setUp()`, el fix de `ROOT_URLCONF` nunca se ejecuta aunque la clase base sea
  `SintelTenantTestCase`.
- Tambien crea `self.user` (admin), `self.membership` (`TenantMembership` rol=ADMIN), y
  sobreescribe `self.client` con `Client(HTTP_HOST=self.domain.domain)` + `force_login`, y crea
  `self.api_client` (`APIClient` autenticado).
- `setup_tenant()`/`setup_domain()` son classmethods con defaults razonables, pero **cualquier
  subclase que los sobreescriba (patron comun en el listado de 34) sigue ganando** por resolucion
  normal de metodos -- no hay conflicto al migrar la base class.

## 3. Tabla de clasificacion (34 archivos)

| # | Archivo | Clasificacion | Razon (evidencia) | Notas |
|---|---|---|---|---|
| 1 | `apps/tenant/facturas/tests/test_create_with_anexos.py` | ALREADY_SAFE | Sin `reverse()`, sin `self.client`; llama `crear_factura()` directamente (linea 45) | `super().setUp()` presente (linea 17) |
| 2 | `apps/tenant/facturas/tests/test_factura_detail_anexos_api.py` | MIGRATE_SAFE | `reverse("factura-detail", ...)` (linea 51) + `self.client.get()` (linea 52); `super().setUp()` en linea 22 | -- |
| 3 | `apps/tenant/facturas/tests/test_facturas_list_detail_payloads.py` | MIGRATE_SAFE | `reverse("factura-list")` (linea 46) + `self.client.get()`; `super().setUp()` linea 15 | -- |
| 4 | `apps/tenant/facturas/tests/test_facturas_list_naturaleza_api.py` | MIGRATE_SAFE | `reverse("factura-list")` (linea 55) + `self.client.get()`; `super().setUp()` linea 15 | -- |
| 5 | `apps/tenant/facturas/tests/test_import_ubl_heavy_payload.py` | MIGRATE_SAFE | `reverse("factura-upload-ubl")` (linea 91) + `self.client.post()`; `super().setUp()` linea 79 | -- |
| 6 | `apps/tenant/facturas/tests/test_importar_ubl_service.py` | ALREADY_SAFE | Sin `reverse()`/`self.client`; llama `importar_ubl()` directamente | `super().setUp()` linea 90; docstring linea 4 dice "Requieren... TenantTestCase" pero es solo por schema, no por URL |
| 7 | `apps/tenant/facturas/tests/test_ingesta_ubl.py` | ALREADY_SAFE | Sin `reverse()`/`self.client`; llama `procesar_factura_xml_task()` y `fast_get_cufe()` directamente | Sin `setUp()` propio. Metodos usan `@pytest.mark.django_db` sobre una clase `TenantTestCase` (redundante pero inofensivo) |
| 8 | `apps/tenant/facturas/tests/test_materializar_from_dto.py` | ALREADY_SAFE | Sin `reverse()`/`self.client`; llama `materializar_factura_desde_result()` directamente | `super().setUp()` linea 63 |
| 9 | `apps/tenant/facturas/tests/test_naturaleza_import_ubl.py` | MIGRATE_SAFE | `reverse("factura-upload-ubl")` en helper `_post_upload()` (linea 141) + `self.client.post()`; `super().setUp()` linea 128 | El propio docstring (lineas 6-44) documenta que el archivo **ya esta roto hoy** por 3 causas independientes (fixture XML desactualizado, contrato de `async` cambiado) y es candidato a eliminar/consolidar. El swap de base class es seguro pero **no** arregla el archivo por si solo |
| 10 | `apps/tenant/facturas/tests/test_naturaleza_rule_ssot.py` | ALREADY_SAFE | Sin `reverse()`/`self.client`; solo prueba funciones puras `_determinar_naturaleza`/`_norm_nit` | `super().setUp()` linea 15 |
| 11 | `apps/tenant/facturas/tests/test_services_ingest_integration.py` | ALREADY_SAFE | Sin `reverse()`/`self.client`; llama `importar_ubl_sync()` con mock | `super().setUp()` linea 20 |
| 12 | `apps/tenant/facturas/tests/test_ssot_empresa_provider.py` | ALREADY_SAFE | Sin `reverse()`/`self.client`; llama `get_empresa_emisor_data()` directamente | Sin `setUp()` propio |
| 13 | `apps/tenant/facturas/tests/test_upload_async_flow.py` | MIGRATE_SAFE | `reverse("factura-upload-ubl")` (linea 75), `reverse("factura-ingest-status", ...)` (linea 86), `reverse("factura-materialize")` (linea 97) + `self.client`; `super().setUp()` linea 58 | -- |
| 14 | `apps/tenant/facturas/tests/test_xml_pipeline_canonical.py` | MIGRATE_SAFE | `reverse("factura-upload-ubl")` (linea 90) + `self.client.post()`; `super().setUp()` linea 55 | Modulo entero saltado hoy via `pytestmark = pytest.mark.skip(...)` (linea 9) -- el swap es seguro pero inerte hasta que se re-active el test |
| 15 | `apps/tenant/core/tests/test_documentos_upload_api.py` | ALREADY_SAFE | Sin `reverse()`; URLs escritas a mano (`/api/v1/documentos/upload/`, lineas 35, 80, 97...) | `setUp()` (linea 22) **no llama `super().setUp()`** -- reemplaza `self.client` por un `APIClient()` sin `HTTP_HOST`. Irrelevante para el bug de `reverse()`, pero riesgo aparte no cubierto por este audit (routing de host) |
| 16 | `apps/tenant/core/tests/test_workspace_facturas_links_and_column.py` | MIGRATE_SAFE | `reverse("tenant-workspace")` envuelto en `try/except` (linea 18) + `self.client.get()`; `super().setUp()` linea 14 | Hoy el `except:` desnudo enmascara el `NoReverseMatch` y siempre usa el fallback `/workspace/`; tras migrar, `reverse()` exitosa cambiara el comportamiento (usara la URL real resuelta) -- verificar que coincide con `/workspace/` |
| 17 | `apps/tenant/core/tests/test_workspace_facturas_modal.py` | MIGRATE_SAFE | `_url_exists()` llama `reverse()` en `try/except` (lineas 29-35) para "workspace"/"tenant-workspace"/"dashboard"; `super().setUp()` linea 19 | Mismo enmascaramiento que #16 |
| 18 | `apps/tenant/core/tests/test_workspace_links_strict.py` | MIGRATE_SAFE | 2 clases, mismo patron `_url_exists()`/`reverse()` en `try/except` (lineas 31-37, 53-59); `super().setUp()` lineas 21, 44 | Mismo enmascaramiento que #16/#17 |
| 19 | `apps/tenant/perfil/tests/test_models.py` | ALREADY_SAFE | Sin `reverse()`/`self.client`; solo ORM (`TenantProfile.objects.create`) | Sin `setUp()` propio |
| 20 | `tests/api/test_upload_document_endpoint_gasto.py` | ALREADY_SAFE | Sin `reverse()`; URLs escritas a mano (`/api/v1/core/documentos/upload/`) | `setUp()` (linea 24) no llama `super().setUp()` |
| 21 | `tests/api/test_upload_document_endpoint_inventario.py` | ALREADY_SAFE | Sin `reverse()`; URL escrita a mano | `setUp()` (linea 23) no llama `super().setUp()` |
| 22 | `tests/multitenant/test_cross_tenant_isolation.py` | ALREADY_SAFE | Sin `reverse()`, sin `self.client`; usa `tenant_context()` + `ingest_document()` directo | `setUp()` (linea 20) no llama `super().setUp()`; crea sus propios tenants adicionales (`acme`, `globant`) mas alla del tenant por defecto |
| 23 | `tests/multitenant/test_tenant_routing_upload_document.py` | ALREADY_SAFE | Sin `reverse()`; URLs escritas a mano con `HTTP_HOST=f"{self.tenant.schema_name}.localhost"` explicito (linea 44, 62) | `setUp()` (linea 25) no llama `super().setUp()`; usa `self.tenant` (provisto por `setUpClass`, funciona igual con ambas bases) |
| 24 | `tests/public/tenants/test_domain_activation.py` | ALREADY_SAFE | Sin `reverse()`; usa `Client(HTTP_HOST=domain.domain)` propio con path `"/"` (linea 109-110) | `setUp()` (linea 26) no llama `super().setUp()`; prueba el servicio `crear_tenant()` propio, crea tenants adicionales manualmente |
| 25 | `tests/tenant/core/smoke/test_workspace_empresa_integridad.py` | MIGRATE_SAFE | Sin `reverse()`; URLs a mano (`/api/v1/empresas/`, `/workspace/#empresa`) + `self.client.force_login(self.user)` (lineas 96, 132, 179, 273) | **La clase no define `setUp()` propio y hereda del shim `apps/tenant/core/tests/base_test.py` que reexporta el `TenantTestCase` crudo** -- `self.user` nunca se crea. Esto es un `AttributeError` real hoy (si el gate de `cryptography`/`playwright`, lineas 14-21, no lo salta). Migrar a `SintelTenantTestCase` provee `self.user`/`self.client` y **corrige** el test, no solo lo hace URL-safe |
| 26 | `tests/tenant/core/smoke/test_workspace_empresa_modules_smoke.py` | UNKNOWN | -- | **Archivo con `SyntaxError` confirmado** (`python -m ast.parse` -> `expected an indented block after function definition on line 21 (line 22)`). El bloque de guard `import pytest / try: import cryptography...` (lineas 22-28) quedo pegado sin indentar dentro de `def test_workspace_empresa_tab_loads(self):` (linea 21), rompiendo el modulo. El archivo no puede ni importarse hoy, independientemente de la base class. Ademas, igual que #25, usa `self.client.force_login(self.user)` (linea 31 y siguientes) sin definir `setUp()` -- mismo problema de `self.user` faltante que #25, una vez arreglada la sintaxis. Requiere intervencion humana para decidir el fix de indentacion antes de clasificar la migracion de base class |
| 27 | `tests/tenant/core/test_admin_integration.py` | ALREADY_SAFE | Sin `reverse()`; URL a mano `/admin/` (linea 79) | Sobreescribe `setup_tenant`/`setup_domain` (lineas 29-49, ganan por herencia normal); `super().setUp()` linea 53 |
| 28 | `tests/tenant/core/test_workspace_crud_integration.py` | MIGRATE_WITH_FIX | 3 clases, todas con `reverse("workspace")` (lineas 41, 47, 66, 85, 102, 122, 138, 170, 183...) + `self.client.get()` | **Las 3 clases sobreescriben `setUp()` sin llamar `super().setUp()`** (lineas 30-37, 160-166, 253-259) -- si solo se cambia la base class, el fix de `ROOT_URLCONF` de `SintelTenantTestCase.setUp()` nunca se ejecuta y `reverse("workspace")` seguira fallando. **Fix necesario:** agregar `super().setUp()` al inicio de los 3 `setUp()` |
| 29 | `tests/tenant/critical/test_auth_authorization.py` | ALREADY_SAFE | Sin `reverse()`; URLs a mano (`/admin/login/`, `/api/v1/core/health/`) | 2 clases, sobreescriben `setup_tenant` (lineas 26-33, 143-150); usan `django_tenants.test.client.TenantClient` propio (no el `self.client` de Sintel); `super().setUp()` presente (lineas 37, 154) |
| 30 | `tests/tenant/critical/test_data_isolation.py` | ALREADY_SAFE | Sin `reverse()`, sin `self.client`; solo ORM + `schema_context()` para crear/validar tenants B manualmente | Sobreescribe `setup_tenant` (linea 26-36); `super().setUp()` linea 40 |
| 31 | `tests/tenant/critical/test_functional_basic.py` | ALREADY_SAFE | `reverse` importado (linea 9) pero **nunca invocado** en el cuerpo del archivo; sin `self.client` | 3 clases, cada una sobreescribe `setup_tenant`; solo 1 de 3 define `setUp()` (con `super().setUp()`, linea 40) |
| 32 | `tests/tenant/gastos/test_gasto_materialization.py` | ALREADY_SAFE | Sin `reverse()`/`self.client`; llama `materializar_gasto_desde_dto()` directo | Sin `setUp()` propio |
| 33 | `tests/tenant/inventario/test_inventario_materialization.py` | ALREADY_SAFE | Sin `reverse()`/`self.client`; llama `materializar_inventario_desde_dto()` directo | `super().setUp()` linea 22 |
| 34 | `tests/tenant/security/test_isolation.py` | ALREADY_SAFE | Sin `reverse()`; URLs a mano (`/dashboard/`, `/api/v1/empresa/empresas/`); usa `Client()`/`APIClient()` propios creados en cada test, no `self.client` | `setUp()` (linea 43) no llama `super().setUp()`; gestiona sus propios 2 tenants (`tenant_a`/`tenant_b`) manualmente via `connection.set_schema()` -- diseno deliberado de "red team" cross-tenant, pero no depende de nada exclusivo de `TenantTestCase` crudo que `SintelTenantTestCase` no darĂ­a (de hecho no llama a ningun `setUp()` de la base) |

## 4. Tally final

| Clasificacion | Cantidad |
|---|---|
| MIGRATE_SAFE | 11 |
| MIGRATE_WITH_FIX | 1 |
| KEEP_INTENTIONAL | 0 |
| ALREADY_SAFE | 21 |
| UNKNOWN | 1 |
| **Total** | **34** |

Ningun archivo calificó como `KEEP_INTENTIONAL`: los archivos que crean tenants/schemas manualmente
(`test_data_isolation.py`, `test_isolation.py`, `test_cross_tenant_isolation.py`,
`test_domain_activation.py`) lo hacen sin depender de ningun comportamiento exclusivo de
`TenantTestCase` crudo que `SintelTenantTestCase` no reproduzca (la mayoria ademas ni siquiera
llama `super().setUp()`, asi que el cambio de base class es inerte para ellos).

## 5. Listos para migrar (MIGRATE_SAFE) -- para el swap mecanico

```
apps/tenant/facturas/tests/test_factura_detail_anexos_api.py
apps/tenant/facturas/tests/test_facturas_list_detail_payloads.py
apps/tenant/facturas/tests/test_facturas_list_naturaleza_api.py
apps/tenant/facturas/tests/test_import_ubl_heavy_payload.py
apps/tenant/facturas/tests/test_naturaleza_import_ubl.py
apps/tenant/facturas/tests/test_upload_async_flow.py
apps/tenant/facturas/tests/test_xml_pipeline_canonical.py
apps/tenant/core/tests/test_workspace_facturas_links_and_column.py
apps/tenant/core/tests/test_workspace_facturas_modal.py
apps/tenant/core/tests/test_workspace_links_strict.py
tests/tenant/core/smoke/test_workspace_empresa_integridad.py
```

Swap mecanico para estos 11: `from django_tenants.test.cases import TenantTestCase` ->
`from tests.tenant.base_test import SintelTenantTestCase` y cambiar la(s) clase(s) base. No
requieren ningun otro cambio para ser seguros de migrar (aunque #9 y #14 seguiran fallando/skipped
por razones ya documentadas ajenas al bug de `ROOT_URLCONF`, y #16-18 cambiaran de comportamiento
al dejar de enmascarar el `NoReverseMatch`).

**Requiere fix adicional (no incluir en el swap mecanico puro sin el fix):**
`tests/tenant/core/test_workspace_crud_integration.py` -- agregar `super().setUp()` a las 3
clases (lineas 30, 160, 253) ademas del swap de base class.

**Bloqueado, necesita triage humano antes de tocar:**
`tests/tenant/core/smoke/test_workspace_empresa_modules_smoke.py` -- `SyntaxError` preexistente
(linea 22), no relacionado con esta migracion.
