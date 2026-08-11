# F27 — Test Inventory (real, verified)

Static inventory of the test suite, built by grepping the actual files on
branch `feat/onboarding-cookie` (no tests were executed). Purpose: give F27
("selective/non-redundant suite before adding new tests") a factual map of
what exists, which base classes are in play, and where the `facturas`
domain has candidate duplicate coverage.

**Methodology.** For every `test_*.py` file under `apps/**/tests/` and
`tests/**`: (1) `find`/`grep -c` for hard counts, (2) `grep -oE "^class
\w+\(...\)"` to capture the declared base class(es), (3) `grep -c "def
test_"` per file, (4) `grep -oE "def test_\w+"` to list test names, used to
write the one-line summaries. Summaries are inferred from file name, class
name, and the actual test method names — **not** from reading full file
bodies. Where a domain is large and low-priority for F27, the row set is
still complete (every file is listed) but summaries are terser.

---

## 1. Totals (verified by command, not estimated)

| Metric | Count | Command |
|---|---|---|
| Test files, `apps/**/tests/**/test_*.py` | **158** | `find apps -path "*/tests/*" -name "test_*.py" \| wc -l` |
| Test files, `tests/**/test_*.py` | **231** | `find tests -name "test_*.py" \| wc -l` |
| **Total test files** | **389** | sum |
| `def test_*` functions/methods, apps/ | **771** | `grep -rc "def test_" --include="test_*.py" apps \| awk -F: '{s+=$2} END{print s}'` |
| `def test_*` functions/methods, tests/ | **1237** | same, over `tests/` |
| **Total test functions** | **2008** | sum |
| Non-test support files in `apps/**/tests/` (conftest.py, base.py, factories.py — not counted above) | 20 | `find apps -path "*/tests/*" -name "*.py" ! -name "__init__.py" ! -name "test_*.py"` |
| Non-test support files in `tests/**` (conftest.py x4, base_test.py, factories.py x2) | 7 | `find tests -name "*.py" ! -name "__init__.py" ! -name "conftest.py" ! -name "test_*.py"` |

The task brief's estimates (~178 apps files, ~232 tests/ files) were counting
all `.py` files including these support files; the actual **test** file
counts (files that contain `def test_*`) are 158 and 231 respectively.

---

## 2. Breakdown by base test class

A file can declare more than one class (helper/base classes co-located with
real test classes, or multiple TestCase subclasses in one file), so the
per-class counts below are "files where this base class appears at least
once" and do not sum to 389.

| Base class | Files (contains at least once) | Notes |
|---|---|---|
| `apps.tenant.core`/`tests.tenant.base_test`.**SintelTenantTestCase** | **138** | Preferred pattern — no shared-schema contamination risk (per-test isolation). |
| `django_tenants.test.cases.TenantTestCase` (raw) | **34** | **Contamination-risk candidates** — see §3. Shares a "test" tenant schema across the file/class; suspected of cross-file bleed in large pytest runs. |
| `apps.tenant.api.tests.base`.**TenantAPITestCase** | 13 | DRF-flavored tenant API test base (found in facturas, contabilidad, empleados, dashboard, empresa). Needs confirmation whether it wraps `SintelTenantTestCase` or raw `TenantTestCase` — not verified in this pass, flagged for follow-up. |
| Plain `django.test.TestCase` | 28 | Mostly public-schema tests (`apps/public/*`, `tests/public/*`) where tenant isolation is not the concern. |
| `tests.public.*`.**PublicAPITestCase** | 8 | Public-schema DRF API tests (accounts, console, impuestos, tenants). |
| `django.test.SimpleTestCase` | 7 | No DB access — template/static-file/string assertion tests. |
| `rest_framework.test.APITestCase` (bare DRF) | 1 | `apps/tenant/proyectos/tests/test_tareas_diarias.py`. |
| `django.test.TransactionTestCase` | 1 | `tests/tenant/empresa/test_empresa_singleton_db.py` (needs real transaction semantics for a unique-constraint/concurrency test). |
| `unittest.TestCase` (bare, no Django) | 1 | `tests/docker/test_docker.py` (shells out to Docker CLI). |
| No class / pytest bare-function or bare `class Foo:` style (`@pytest.mark.django_db`) | **161** | See breakdown below. |

Pytest-style breakdown of the 161 "no declared base class" files (verified
by re-grepping each for `^class `):
- **63** are `class TestFoo:` (no parens) decorated with `@pytest.mark.django_db` — pytest-native class style, not unittest.
- **98** have no `class` at all — pure `def test_...()` functions, typically using `pytest.fixture`/`django_db` marks.

### 2a. Files under `apps/tenant/facturas/tests/` and `apps/tenant/*/tests/` using raw `TenantTestCase`

All 34 raw-`TenantTestCase` files repo-wide (contamination-risk candidates — the other 355 files use `SintelTenantTestCase`, plain `TestCase`, or are pytest-style and are not implicated in the schema-sharing issue):

**`apps/tenant/facturas/tests/` (14 of 30 facturas files — the largest single concentration):**
- `test_create_with_anexos.py`
- `test_factura_detail_anexos_api.py`
- `test_facturas_list_detail_payloads.py`
- `test_facturas_list_naturaleza_api.py`
- `test_import_ubl_heavy_payload.py`
- `test_importar_ubl_service.py`
- `test_ingesta_ubl.py`
- `test_materializar_from_dto.py`
- `test_naturaleza_import_ubl.py`
- `test_naturaleza_rule_ssot.py`
- `test_services_ingest_integration.py`
- `test_ssot_empresa_provider.py`
- `test_upload_async_flow.py`
- `test_xml_pipeline_canonical.py`

**Other `apps/tenant/*/tests/` (4 files):**
- `apps/tenant/core/tests/test_documentos_upload_api.py`
- `apps/tenant/core/tests/test_workspace_facturas_links_and_column.py`
- `apps/tenant/core/tests/test_workspace_facturas_modal.py`
- `apps/tenant/core/tests/test_workspace_links_strict.py`
- `apps/tenant/perfil/tests/test_models.py`

**`tests/tenant/*` and other `tests/**` (15 files):**
- `tests/api/test_upload_document_endpoint_gasto.py`
- `tests/api/test_upload_document_endpoint_inventario.py`
- `tests/multitenant/test_cross_tenant_isolation.py`
- `tests/multitenant/test_tenant_routing_upload_document.py`
- `tests/public/tenants/test_domain_activation.py`
- `tests/tenant/core/smoke/test_workspace_empresa_integridad.py`
- `tests/tenant/core/smoke/test_workspace_empresa_modules_smoke.py`
- `tests/tenant/core/test_admin_integration.py`
- `tests/tenant/core/test_workspace_crud_integration.py`
- `tests/tenant/critical/test_auth_authorization.py`
- `tests/tenant/critical/test_data_isolation.py`
- `tests/tenant/critical/test_functional_basic.py`
- `tests/tenant/gastos/test_gasto_materialization.py`
- `tests/tenant/inventario/test_inventario_materialization.py`
- `tests/tenant/security/test_isolation.py`

Notably, **`tests/tenant/facturas/` (15 files, the parallel top-level facturas
suite) uses `SintelTenantTestCase` everywhere, zero raw `TenantTestCase`** —
so the contamination risk in the facturas domain is concentrated entirely in
`apps/tenant/facturas/tests/`, not in the `tests/tenant/facturas/` tree.

---

## 3. Facturas domain — duplicate/overlap candidates (evidence, not verdicts)

Facturas has **two parallel test locations**:
- `apps/tenant/facturas/tests/` — 30 files, 129 test functions (colocated FSD tests)
- `tests/tenant/facturas/` — 15 files (+1 in `smoke/`), 62 test functions (top-level integration suite)

Both exercise the same `FacturaViewSet` / upload-UBL / list / delete
contract. Below are the strongest overlap candidates found by comparing
test names and class docstrings-by-name; each is flagged with the concrete
evidence, not a dedup recommendation (that's out of scope for this pass).

### 3a. Upload-UBL endpoint — tested independently in at least 6 files

| File | Location | Base class | Relevant tests |
|---|---|---|---|
| `test_api_upload_ubl_contract.py` | apps | SintelTenantTestCase | `test_post_upload_ubl_creates_factura`, `test_xml_endpoint_returns_xml`, `test_multi_tenant_isolation` |
| `test_import_ubl_heavy_payload.py` | apps | TenantTestCase | `test_upload_heavy_ok`, `test_list_no_incluye_blobs`, `test_detail_incluye_anexos` |
| `test_upload_async_flow.py` | apps | TenantTestCase | `test_async_flow_completo`, `test_sync_flow_directo`, `test_upload_sin_archivo_retorna_400` |
| `tests/tenant/facturas/test_api_e2e.py` | tests/ | SintelTenantTestCase | `test_upload_ubl_valid_xml_returns_201`, `test_upload_ubl_missing_file_returns_400_missing_xml`, `test_upload_ubl_invalid_naturaleza_returns_400_invalid_param`, `test_upload_duplicate_returns_409` |
| `tests/tenant/facturas/test_api_facturas_forensics.py` | tests/ | SintelTenantTestCase | `test_upload_missing_xml_returns_400`, `test_upload_preview_ok`, `test_upload_persist_then_detail_and_delete`, `test_upload_invalid_naturaleza_returns_400`, `test_upload_duplicate_returns_409` |
| `tests/tenant/facturas/test_api_facturas_minimal.py` | tests/ | SintelTenantTestCase | `test_upload_missing_xml_400`, `test_upload_preview_200`, `test_upload_persist_201_o_200`, `test_delete_204` |
| `tests/tenant/facturas/test_api_facturas_regression.py` | tests/ | SintelTenantTestCase | `test_upload_ok_preview_returns_200`, `test_upload_invalid_is_400_not_500` |
| `tests/tenant/facturas/test_upload_ubl_minimal_errors.py` | tests/ | SintelTenantTestCase | `test_upload_invalid_xml_returns_400_dto_parse_error`, `test_upload_missing_file_or_xml_returns_400_missing_xml`, `test_upload_invalid_naturaleza_returns_400_invalid_param`, `test_upload_duplicate_numero_returns_409_duplicate`, `test_upload_valid_xml_returns_201_created`, `test_upload_preview_returns_200_ok` |
| `tests/tenant/facturas/test_upload_ubl_smoke.py` | tests/ | SintelTenantTestCase | `test_upload_ubl_handles_vendor_prefixes`, `test_upload_ubl_without_file_or_xml_returns_400`, `test_upload_ubl_invalid_xml_returns_400` |

**Evidence:** `test_api_e2e.py`, `test_api_facturas_forensics.py`,
`test_api_facturas_minimal.py`, `test_api_facturas_regression.py`, and
`test_upload_ubl_minimal_errors.py` (all in `tests/tenant/facturas/`) each
independently assert **the identical four contract facts** — missing-file
returns 400, invalid `naturaleza` returns 400, duplicate upload returns 409,
valid upload returns 200/201 — against the same upload endpoint, with only
the assertion phrasing and status-code-vs-message granularity differing.
The class names themselves (`Forensics`, `Minimal`, `Regression`, `E2E`,
`MinimalErrors`) read as successive "let's redo this test file" passes
rather than distinct contracts. `test_upload_ubl_smoke.py` overlaps the
same missing-file/invalid-xml assertions again. This is the single richest
dedup opportunity in the repo.

### 3b. Facturas list endpoint (`GET /facturas/`) — tested in 3+ files just for "returns 200"

| File | Tests |
|---|---|
| `tests/tenant/facturas/test_facturas_endpoint_smoke.py` | `test_listado_facturas_devuelve_200`, `test_listado_facturas_vacio_devuelve_200`, `test_listado_facturas_404_en_dominio_publico` |
| `tests/tenant/facturas/test_facturas_min.py` | `test_get_facturas_returns_200`, `test_get_facturas_with_estado_filter_returns_200` |
| `tests/tenant/facturas/smoke/test_facturas_list.py` | `test_list_facturas_returns_200`, `test_list_facturas_empty_returns_200`, `test_list_facturas_404_from_public_domain` |

**Evidence:** `test_facturas_endpoint_smoke.py` and
`smoke/test_facturas_list.py` assert near-verbatim the same three facts
(200 with data, 200 empty, 404 from public domain) — the test names are
translations of each other (Spanish vs English) for what looks like the
same three assertions. `test_facturas_min.py` is a narrower subset of the
same "list returns 200" contract.

### 3c. Naturaleza (venta/compra) classification rule — tested in 4 files at different layers

| File | Location | Layer tested |
|---|---|---|
| `test_naturaleza_rule_ssot.py` | apps | Pure unit: `norm_nit`, decision function directly |
| `test_naturaleza_unit.py` | apps | Pure unit: `TestNormNit`, `TestDecision` — same `norm_nit`/decision functions, different test class split |
| `test_naturaleza_import_ubl.py` | apps | Integration: `preview_venta`/`preview_compra` through the UBL import path |
| `test_facturas_list_naturaleza_api.py` | apps | API: list endpoint exposes correct `naturaleza` |
| `tests/tenant/facturas/test_facturas_filters_api.py` | tests/ | API: `filter_by_naturaleza_venta`/`filter_by_naturaleza_compra` |

**Evidence:** `test_naturaleza_rule_ssot.py` and `test_naturaleza_unit.py`
both test the same normalization function (`norm_nit`) with near-identical
case names (`norm_nit_elimina_separadores`/`norm_formats_con_separadores`,
`norm_nit_maneja_dv`/`norm_con_dv`, `norm_nit_maneja_none`/`norm_none_vacio`)
— this pair is the clearest unit-level duplicate in facturas, both using
`SimpleTestCase`. `test_naturaleza_import_ubl.py` re-derives the same
venta/compra assertions (`persistencia_asigna_naturaleza_venta`,
`persistencia_asigna_naturaleza_compra`) that also appear verbatim in
`test_importar_ubl_service.py` (`test_persistencia_asigna_naturaleza_venta`,
`test_persistencia_asigna_naturaleza_compra` — identical names).

### 3d. `test_importar_ubl_service.py` vs `test_naturaleza_import_ubl.py`

Test names `test_preview_compra`, `test_persistencia_asigna_naturaleza_venta`,
`test_persistencia_asigna_naturaleza_compra` appear **verbatim identical**
in both files (`apps/tenant/facturas/tests/test_importar_ubl_service.py`
and `apps/tenant/facturas/tests/test_naturaleza_import_ubl.py`). Same base
class (`TenantTestCase`), same import path under test
(`ImportarUblService`/UBL preview+persist). This is the strongest
same-file-name-collision-level evidence in the whole inventory — worth
checking first when F27 moves to the dedup/removal phase.

### 3e. Facturas models/services — light overlap

`tests/tenant/facturas/test_models_facturas.py` (`test_factura_auto_total`,
`test_factura_numero_unico`, `test_factura_campos_requeridos`) and
`tests/tenant/facturas/test_facturas_services.py`
(`test_crear_factura_recalcula_totales_desde_items`,
`test_actualizar_factura_recalcula_totales`) both assert total-recalculation
behavior on `Factura`, from the model-signal side and the service side
respectively — plausibly two views of one behavior rather than a pure
duplicate; flagged for the dedup phase to confirm which layer is
authoritative.

### 3f. Devoluciones (Nota de Crédito) — recently added, currently non-overlapping

`test_devolucion_nota_credito.py` (SintelTenantTestCase, 5 tests, idempotency
by CUDE/CUFE on `ENTRADA_DEVOLUCION` movements) and
`test_nota_credito_pipeline.py` (SintelTenantTestCase, 12 tests, numbered
`test_1_..test_12_` smoke pipeline covering parse/preview/persist/API
contract/immutability/delete) both exercise the NC → `ItemNotaCredito` →
`ENTRADA_DEVOLUCION` pipeline added in the last 5 commits on this branch,
but at different grain (business-rule edge cases vs end-to-end pipeline
smoke) — no verbatim test-name collisions found; **not** flagged as
duplicate, listed here only because it's the newest code and the most
likely place new F27 tests would be tempted to pile on redundantly.

### 3g. Bonus finding outside facturas — byte-identical duplicate file

Not part of the facturas ask, but too clear-cut to omit:
**`tests/celery/test_tasks_import.py` and
`tests/celery_tasks/test_tasks_import.py` are byte-identical** (`diff`
reports zero differences) — same 3 tests
(`test_onboard_task_import_and_call_smoke`,
`test_crear_tenant_con_owner_re_export`, `test_celery_app_autodiscovery`)
run twice under two different top-level dirs (`tests/celery/` vs
`tests/celery_tasks/`). Cheapest possible dedup win once F27 reaches that
phase.

---

## 4. Full per-file inventory, by app/domain

Columns: **File** (relative to repo root) · **Base class(es)** (`;`-joined
if multiple classes declared in the file) · **#test** (`def test_` count) ·
**Summary** (inferred from class/file name + test method names, not full
file reads).

### 4.1 `apps/tenant/facturas/tests/` (30 files, 129 tests)

| File | Base class | # | Summary |
|---|---|---|---|
| test_api_facturas.py | TenantAPITestCase (x2 classes) | 11 | FacturaViewSet + ItemFacturaViewSet: list/detail/create-blocked/estado actions/filter/search. |
| test_api_upload_ubl_contract.py | SintelTenantTestCase | 4 | Upload-UBL contract: creates factura, list excludes heavy XML fields, XML endpoint, multi-tenant isolation. |
| test_create_with_anexos.py | TenantTestCase | 3 | Creating factura with/without anexos (attachments), UBL-XML-only case. |
| test_devolucion_nota_credito.py | SintelTenantTestCase | 5 | NC devoluciones: item resoluble genera ENTRADA_DEVOLUCION, item sin match, multi-item, reimport idempotente por CUDE, NC sin items no rompe flujo previo. |
| test_factura_detail_anexos_api.py | TenantTestCase | 6 | Detail endpoint meta/anexos: get UBL XML, get app response, 404 sin anexos. |
| test_facturas_delete_api.py | SintelTenantTestCase | 5 | Delete endpoint: ok/404/cascade anexos/response format/no-500. |
| test_facturas_list_detail_payloads.py | TenantTestCase | 2 | List returns minimal payload; detail includes anexos. |
| test_facturas_list_naturaleza_api.py | TenantTestCase | 1 | List includes correct `naturaleza` field. |
| test_import_ubl_heavy_payload.py | TenantTestCase | 3 | Heavy UBL upload; list excludes blobs; detail includes anexos. |
| test_importar_ubl_service.py | TenantTestCase | 5 | ImportarUblService: 422 sin empresa, 200 con empresa+venta, preview compra, naturaleza venta/compra persistencia (names collide with test_naturaleza_import_ubl.py — see §3d). |
| test_ingesta_ubl.py | TenantTestCase | 2 | `fast_get_cufe`, procesar_factura_xml celery task. |
| test_materializar_from_dto.py | TenantTestCase | 7 | Materialize-from-DTO: compra/venta vs SSoT, idempotencia por CUFE/numero, dos facturas sin CUFE no chocan, 422 sin empresa. |
| test_multitenant_isolation_tabla_html.py | (pytest, no class) | 1 | Cross-tenant isolation on the facturas table HTML fragment. |
| test_naturaleza_import_ubl.py | TenantTestCase | 5 | Naturaleza preview/persist venta+compra via UBL import (names overlap test_importar_ubl_service.py). |
| test_naturaleza_rule_ssot.py | TenantTestCase | 8 | Pure unit tests of `norm_nit` + venta/compra decision function (overlaps test_naturaleza_unit.py — see §3c). |
| test_naturaleza_unit.py | SimpleTestCase (x2 classes) | 11 | `TestNormNit` + `TestDecision` — same norm_nit/decision logic as above, split differently. |
| test_nota_credito_pipeline.py | SintelTenantTestCase | 12 | Numbered end-to-end NC pipeline smoke: detect parser, preview, persist idempotencia CUDE, one-to-one link, API contract, immutability, delete rollback. |
| test_organizational_context_adoption.py | SintelTenantTestCase | 2 | `get_organizational_context` SSOT adoption checks on FacturaViewSet. |
| test_payload_split.py | SimpleTestCase | 5 | Splitting DTO payload into factura fields vs anexos. |
| test_retenciones_backward_compat.py | TenantAPITestCase (x3 classes) | 14 | Backward-compat of retefuente/reteica/reteiva properties on Factura + ItemFactura + API read-only fields. |
| test_scope_bridges_f9.py | SintelTenantTestCase | 3 | F9 alcance/sede: cotizacion-bridge scope rules for linking cotizaciones. |
| test_scope_facturas_f11.py | SintelTenantTestCase | 6 | F11 object-level scope: sede/empresa access to individual facturas by UUID, patch sede assignment. |
| test_scope_isolation_f14.py | SintelTenantTestCase | 2 | F14 sede isolation: no sedes asignadas -> ve nada; dos sedes asignadas -> ve ambas. |
| test_scope_selectors_f7.py | SintelTenantTestCase | 2 | F7 selector-level scope: alcance sede vs empresa on the base queryset. |
| test_scope_ventas_facturas_f10.py | SintelTenantTestCase | 3 | F10: crear factura desde venta propaga sede_id (incl. anti-IDOR for nonexistent sede). |
| test_services_ingest_integration.py | TenantTestCase | 2 | Ingest service wiring: importar_ubl_sync invokes ingest_ubl_sync, handles parse errors. |
| test_ssot_empresa_provider.py | TenantTestCase | 4 | SSoT empresa provider contract: raises without empresa/nit, ok with empresa, never returns None. |
| test_templates.py | TenantAPITestCase | 2 | API endpoints must not render HTML templates (API-first guard). |
| test_upload_async_flow.py | TenantTestCase | 5 | Async upload flow: full async, sync direct, missing file 400, status-task 404, materialize-without-dto 400. |
| test_xml_pipeline_canonical.py | TenantTestCase | 4 | Canonical XML pipeline: parser, ingest sync enriched payload, upload uses canonical pipeline, materialize uses canonical DTO. |

### 4.2 `tests/tenant/facturas/` + `tests/tenant/facturas/smoke/` (16 files, 65 tests)

| File | Base class | # | Summary |
|---|---|---|---|
| test_api_e2e.py | SintelTenantTestCase | 6 | Upload-UBL E2E: valid xml 201, missing file 400, invalid naturaleza 400, detail 200, delete 204, duplicate 409 (overlaps §3a). |
| test_api_facturas_forensics.py | SintelTenantTestCase | 5 | Same upload-UBL contract restated as a "forensics" pass (overlaps §3a). |
| test_api_facturas_minimal.py | SintelTenantTestCase | 4 | Same upload-UBL contract, minimal-assertion variant (overlaps §3a). |
| test_api_facturas_regression.py | SintelTenantTestCase | 2 | Same upload-UBL contract, "regression" variant, 2 of the same assertions (overlaps §3a). |
| test_attached_document_smoke.py | SintelTenantTestCase | 2 | AttachedDocument upload with/without invoice context. |
| test_factura_immutability.py | SintelTenantTestCase | 9 | Factura is read/delete-only via API: PUT/PATCH forbidden, create forbidden, delete variants, XML endpoint ok. |
| test_facturas_api.py | SintelTenantTestCase | 7 | Generic facturas API CRUD: auth required, create/update require admin-staff, filter by estado, search by numero. |
| test_facturas_endpoint_smoke.py | SintelTenantTestCase | 3 | List returns 200 (data/empty/404-from-public-domain) (overlaps §3b). |
| test_facturas_filters_api.py | SintelTenantTestCase | 5 | Filter by naturaleza venta/compra, NIT emisor/receptor, date range. |
| test_facturas_min.py | SintelTenantTestCase | 2 | Minimal "list returns 200" + estado filter (overlaps §3b). |
| test_facturas_services.py | SintelTenantTestCase | 3 | Service-layer total recalculation on create/update + import-UBL-crea-factura-completa. |
| test_models_facturas.py | (pytest, no class) | 3 | Model-level: auto total, numero unico, campos requeridos. |
| test_upload_ubl_minimal_errors.py | SintelTenantTestCase | 8 | Upload-UBL error contract, most granular of the upload-UBL files (overlaps §3a). |
| test_upload_ubl_smoke.py | SintelTenantTestCase | 3 | Upload-UBL smoke: vendor prefixes, missing file/xml, invalid xml (overlaps §3a). |
| smoke/test_facturas_list.py | (pytest, no class) | 3 | List returns 200 (data/empty/404-from-public-domain) — near-duplicate of test_facturas_endpoint_smoke.py (§3b). |

### 4.3 `apps/tenant/core/tests/` (17 files, 82 tests)

| File | Base class | # | Summary |
|---|---|---|---|
| test_architecture_ssot.py | (pytest) | 6 | Repo-wide SSOT checks: every tenant model has empresa FK, service layer can't create without empresa. |
| test_documentos_upload_api.py | TenantTestCase | 6 | Generic document-upload API: missing file, preview mode, invalid file, tipo hint, response shape, multitenant isolation. |
| test_organizational_bridges.py | SintelTenantTestCase | 4 | Organizational bridge lookups (cliente/proveedor) respect empresa DSV. |
| test_organizational_context.py | SintelDSVMixin;SintelTenantTestCase | 4 | `resolve()` context matches legacy mixin resolution; anonymous user raises. |
| test_organizational_dsv.py | SintelTenantTestCase | 7 | DSV rejects cross-empresa objects; alcance sede/empresa fail-closed rules. |
| test_organizational_filters.py | SintelTenantTestCase | 3 | `filter_by_scope` strict vs null-safe behavior. |
| test_organizational_permissions.py | mixed (APIView/TestCase/SintelTenantTestCase) | 12 | Role/alcance permission matrix (admin_empresa/admin_sede/jefe_area/operador/consulta) and minimum-level ordering. |
| test_organizational_resolver.py | mixed (View/SintelTenantTestCase) | 6 | Context resolver via JWT, session, plain non-DRF view; scope-plural inclusion. |
| test_organizational_scope.py | SintelTenantTestCase | 8 | Scope resolution: alcance empresa vs sede, active-sede vs full-scope-set distinction. |
| test_organizational_selectors.py | SintelTenantTestCase | 5 | Selector-level scope filtering returns a chainable queryset. |
| test_organizational_service_layer.py | SintelTenantTestCase | 4 | Service-layer resolve_empresa_and_sede / resolve_perfil / crear_orden_compra via context. |
| test_ssot_integrity.py | (pytest) | 6 | Repo-wide model integrity: empresa FK present, base-class inheritance, no duplicate empresa field, audit fields, indexed. |
| test_workspace_401_handler_smoke.py | (pytest) | 1 | 401 handler doesn't redirect for non-critical modules. |
| test_workspace_facturas_links_and_column.py | TenantTestCase | 1 | Workspace facturas tab has naturaleza column + correct assets. |
| test_workspace_facturas_modal.py | TenantTestCase | 3 | Workspace facturas modal present, relative routes, no duplicated assets. |
| test_workspace_facturas_ui_phase3.py | SimpleTestCase | 11 | Phase-3 facturas UI static asserts: template/JS existence, naturaleza badge, CSRF usage. |
| test_workspace_links_strict.py | TenantTestCase (x2 classes) | 5 | Workspace strict-links guard: no duplicated assets, relative API endpoints. |

### 4.4 `apps/tenant/contabilidad/tests/` (13 files, 111 tests)

| File | Base class | # | Summary |
|---|---|---|---|
| test_api_contabilidad.py | TenantAPITestCase (x4) | 12 | Cuentas/asientos/movimientos CRUD API, aprobar action, libro diario with period/date-range params. |
| test_f22_extractor_inventario_integration.py | SintelTenantTestCase | 10 | F22 extractor: entrada compra genera asiento balanceado, no duplica en doble ejecución, periodo cerrado bloquea. |
| test_f22_extractor_inventario_mapping.py | SimpleTestCase | 9 | F22 pure account-mapping rules (debe/haber lines per movement type). |
| test_f22_extractor_inventario_multitenant.py | (pytest) | 1 | Extractor doesn't leak movements across tenants. |
| test_f24_e2e_circuito_completo.py | SintelTenantTestCase | 8 | F24 full circuit: compra/venta E2E to asiento contable, multi-item, multi-sede, idempotencia, periodo cerrado. |
| test_f24_e2e_multitenant_dsv.py | (pytest) | 2 | Cross-tenant producto UUID rejected; full compra/venta circuit isolated per tenant. |
| test_fase1_gastos.py | mixed (TestCase/TenantAPITestCase) | 9 | LineaTransaccion lado debe/haber defaults+overrides; gasto con retefuente/reteica. |
| test_integracion_contabilizador.py | TestCase (x3) | 9 | Contabilizador integration: venta simple, multiples impuestos, centro de costo, inmutabilidad. |
| test_multitenant_isolation.py | (pytest) | 1 | Contabilidad tabla HTML multitenant isolation. |
| test_organizational_context_adoption.py | SintelTenantTestCase | 1 | CuentaContableViewSet organizational-context SSOT adoption. |
| test_retenciones_api.py | TenantAPITestCase (x2) | 16 | Retenciones API: list/filter/search/create/destroy, obtener-por-tercero/documento actions. |
| test_retenciones_service.py | TenantAPITestCase | 14 | RetencionesService: obtener desde tercero/defaults, NIT normalization, monto calculation precision. |
| test_templates.py | TenantAPITestCase | 2 | API endpoints don't render templates. |

### 4.5 `apps/tenant/empleados/tests/` (11 files, 74 tests)

| File | Base class | # | Summary |
|---|---|---|---|
| test_api_smoke.py | (pytest) | 3 | Empleados list/create smoke + multitenancy isolation. |
| test_crud_smoke_v38.py | (pytest) | 21 | Broad CRUD smoke across empleado/contrato/nomina/resolucion/devengo (biggest single test file in the repo by test count in this domain). |
| test_devengos_api_smoke.py | (pytest) | 5 | Devengos list/create smoke, totales calculados, empleados disponibles. |
| test_empleados_crud.py | TenantAPITestCase (x3) | 13 | Empleado/contrato/devengo CRUD with duplicate/uuid/tenant-isolation checks. |
| test_empleados_delete.py | TenantAPITestCase | 4 | Delete/recreate empleado; delete blocked by active contract/payroll. |
| test_multitenant_isolation_tablas_html.py | (pytest) | 2 | Tabla + master-detail HTML multitenant isolation. |
| test_routing_smoke.py | (pytest) | 3 | Devengos routing after include, resoluciones DIAN offcanvas render. |
| test_scope_isolation_f14.py | SintelTenantTestCase | 4 | F14 sede/area isolation for empleados. |
| test_scope_object_level_f13.py | SintelTenantTestCase | 3 | F13 object-level scope by UUID for empleado. |
| test_scope_selectors_f7.py | SintelTenantTestCase | 3 | F7 selector scope incl. area-level filtering. |
| test_scope_write_validation_f8.py | SintelTenantTestCase | 3 | F8 write-time scope validation on sede assignment. |

### 4.6 `apps/tenant/gastos/tests/` (10 files, 22 tests)

| File | Base class | # | Summary |
|---|---|---|---|
| test_auth_session_smoke.py | (pytest) | 1 | Session-auth smoke for gastos list. |
| test_f25_procesar_gasto_atomicidad.py | (pytest) | 2 | F25 atomicity: failure on second retention rolls back both document and first retention. |
| test_fase9_persistence.py | (pytest) | 2 | Full gasto persistence; resolucion with past date is permitted. |
| test_gastos_login_session_loop.py | (pytest) | 1 | No logout-after-login loop for gastos under session auth. |
| test_multitenant_isolation.py | (pytest) | 2 | Gastos + gastos-tabla-html multitenant isolation. |
| test_organizational_context_adoption.py | SintelTenantTestCase | 1 | GastoViewSet organizational-context SSOT adoption. |
| test_proveedor_integration.py | (pytest) | 3 | Gasto with valid/invalid proveedor (DSV), list shows proveedor data. |
| test_scope_isolation_f14.py | SintelTenantTestCase | 2 | F14 sede isolation for gastos. |
| test_scope_object_level_f13.py | SintelTenantTestCase | 5 | F13 object-level scope incl. offcanvas editar/detalle. |
| test_scope_selectors_f7.py | SintelTenantTestCase | 2 | F7 selector scope. |

### 4.7 `apps/tenant/empresa/tests/` (10 files, 22 tests)

| File | Base class | # | Summary |
|---|---|---|---|
| test_api_empresa.py | TenantAPITestCase | 11 | Empresa CRUD API incl. activas action, filter/search, tenant isolation, sedes/areas relationship. |
| test_estructura_organizacional_inicial.py | SintelTenantTestCase | 3 | Auto-creates principal sede/area when empresa has none. |
| test_organizational_context_adoption.py | SintelTenantTestCase | 2 | SedeViewSet organizational-context SSOT adoption. |
| test_services_business.py | (pytest) | 2 | crear_empresa/update_empresa business-service DB call assertions. |
| test_services_crud.py | (pytest) | 2 | qs_list / get_empresa_emisor_data crud-service behavior. |
| test_tabla_areas_view.py | (pytest) | 2 | Areas table render + search. |
| test_tabla_empresa_view.py | (pytest) | 2 | Empresa table render + search. |
| test_tabla_mailinboxconfig_view.py | (pytest) | 2 | MailInboxConfig table render + search. |
| test_tabla_sedes_view.py | (pytest) | 2 | Sedes table render + search. |
| test_templates.py | TenantAPITestCase | 2 | API endpoints don't render templates. |

### 4.8 `apps/tenant/proyectos/tests/` (8 files, 24 tests)

| File | Base class | # | Summary |
|---|---|---|---|
| test_organizational_context_adoption.py | SintelTenantTestCase | 2 | ProyectoViewSet organizational-context SSOT adoption. |
| test_presupuesto_proyecto.py | (pytest) | 5 | Budget calc, DSV on items, cierre blocks create/delete, recalculo on delete. |
| test_proyecto_fase_validation.py | (pytest) | 3 | Borrador phase doesn't require responsables; serializer empty-string-to-none. |
| test_scope_isolation_f14.py | SintelTenantTestCase | 2 | F14 sede isolation. |
| test_scope_object_level_f13.py | SintelTenantTestCase | 4 | F13 object-level scope incl. presupuesto items. |
| test_scope_selectors_f7.py | SintelTenantTestCase | 2 | F7 selector scope. |
| test_tabla_view.py | (pytest) | 2 | Proyectos table KPIs + fase filter. |
| test_tareas_diarias.py | APITestCase | 14 | Tareas diarias: date-range validation, DSV, cierre blocks, estado transitions, unique constraint. |

### 4.9 `apps/tenant/clientes/tests/` (8 files, 24 tests)

| File | Base class | # | Summary |
|---|---|---|---|
| test_auth_session_smoke.py | (pytest) | 2 | Session-auth smoke for clientes + ventas-cliente lists. |
| test_cartera_crud_api.py | (pytest) | 2 | Cartera creation + abono, cartera API endpoints. |
| test_clientes_api_and_service.py | (pytest) | 3 | Service idempotent create, API list smoke, model basics. |
| test_clientes_crud_workspace.py | (pytest) | 3 | Full CRUD, create validations, list filters/ordering. |
| test_contacto_cliente_crud.py | DjangoTestCase (x2) | 14 | ContactoCliente viewset/serializer/model existence + offcanvas/JS asset wiring (largely static-structure assertions). |
| test_idempotence_v2614.py | (pytest) | 7 | Idempotent create (POST x2 == 1), wrong-empresa rejection, serializer empresa_id context. |
| test_organizational_context_adoption.py | SintelTenantTestCase | 2 | ClienteViewSet organizational-context SSOT adoption. |
| test_tabla_view.py | (pytest) | 2 | Clientes table KPIs + tipo filter. |

### 4.10 `apps/tenant/cotizaciones/tests/` (7 files, 13 tests)

| File | Base class | # | Summary |
|---|---|---|---|
| test_api.py | (pytest) | 1 | Create cotizacion via API. |
| test_organizational_context_adoption.py | SintelTenantTestCase | 1 | CotizacionViewSet organizational-context SSOT adoption. |
| test_scope_isolation_f14.py | SintelTenantTestCase | 2 | F14 sede isolation. |
| test_scope_object_level_f13.py | SintelTenantTestCase | 4 | F13 object-level scope incl. detail-by-uuid selector. |
| test_scope_selectors_f7.py | SintelTenantTestCase | 2 | F7 selector scope. |
| test_serializers.py | (pytest) | 2 | Serializer validity (incl. UUID). |
| test_services.py | (pytest) | 1 | Crear cotizacion valida via service. |

### 4.11 `apps/tenant/proveedores/tests/` (6 files, 18 tests)

| File | Base class | # | Summary |
|---|---|---|---|
| test_auth_session_smoke.py | (pytest) | 1 | Session-auth smoke for proveedores + compras-proveedor lists. |
| test_idempotence_v2614.py | (pytest) | 7 | Idempotent create, different-documento creates new, invalid-empresa rejection, serializer context. |
| test_organizational_context_adoption.py | SintelTenantTestCase | 2 | ProveedorViewSet organizational-context SSOT adoption. |
| test_proveedores_api_and_service.py | (pytest) | 3 | Service crear, API list smoke, qs filtered by empresa. |
| test_tabla_cuentas_pagar_view.py | (pytest) | 3 | Cuentas-por-pagar table render, estado filter, search. |
| test_tabla_view.py | (pytest) | 2 | Proveedores table render + cartera vacia, search. |

### 4.12 `apps/tenant/compras/tests/` (6 files, 30 tests)

| File | Base class | # | Summary |
|---|---|---|---|
| test_f21_recepcion_compra.py | SintelTenantTestCase;RecepcionCompraF21TestsBase (x4) | 7 | F21 recepcion: total genera movimiento, dos recepciones parciales completan, exceso rechazado, no duplica al confirmar dos veces. |
| test_f24_confirmar_recepcion_atomicidad.py | SintelTenantTestCase | 2 | F24 atomicity: failure on second item rolls back the first. |
| test_multitenant_isolation_tabla_html.py | (pytest) | 1 | Compras tabla HTML multitenant isolation. |
| test_organizational_context_adoption.py | SintelTenantTestCase | 1 | OrdenCompraViewSet organizational-context SSOT adoption. |
| test_organizational_isolation_empresa_a.py | SintelTenantTestCase | 13 | Sede/empresa alcance matrix: list/retrieve/update/delete across sedes for orden compra. |
| test_scope_pilot_f5.py | SintelTenantTestCase | 7 | F5 pilot scope: API list + tabla HTMX under sede/area/empresa alcance. |

### 4.13 `apps/tenant/inventario/tests/` (5 files, 19 tests)

| File | Base class | # | Summary |
|---|---|---|---|
| test_f21_traslado_inventario.py | SintelTenantTestCase;TrasladoInventarioF21TestsBase (x3) | 9 | F21 traslado: full flow, same-sede rejected, insufficient stock, enviar/cancelar state-machine rules. |
| test_organizational_context_adoption.py | SintelTenantTestCase | 2 | ProductoViewSet organizational-context SSOT adoption. |
| test_scope_isolation_f14.py | SintelTenantTestCase | 2 | F14 sede isolation. |
| test_scope_object_level_f13.py | SintelTenantTestCase | 4 | F13 object-level scope incl. offcanvas. |
| test_scope_selectors_f7.py | SintelTenantTestCase | 2 | F7 selector scope. |

### 4.14 `apps/tenant/ventas/tests/` (4 files, 13 tests)

| File | Base class | # | Summary |
|---|---|---|---|
| test_f23_venta_inventario.py | SintelTenantTestCase | 8 | F23: venta facturada genera movimiento salida usando costo promedio; stock insuficiente revierte venta+factura. |
| test_f23_venta_inventario_multitenant.py | (pytest) | 1 | Venta of one tenant doesn't affect another tenant's stock. |
| test_multitenant_isolation.py | (pytest) | 2 | Ventas + ventas-tabla-html multitenant isolation. |
| test_organizational_context_adoption.py | SintelTenantTestCase | 2 | VentaViewSet organizational-context SSOT adoption. |

### 4.15 `apps/tenant/dashboard/tests/` (4 files, 36 tests)

| File | Base class | # | Summary |
|---|---|---|---|
| test_extractores.py | TestCase (x4) | 13 | Metric extractors: total facturas, pendientes, vencidas, ingresos mes/promedio, empresa inexistente. |
| test_organizational_context_adoption.py | SintelTenantTestCase | 1 | DashboardViewSet organizational-context SSOT adoption. |
| test_simple.py | TestCase (x2) | 11 | Widget DTO construction (facturas/inventario/empleados/gastos/proveedores) + serializer round-trip. |
| test_viewsets.py | TenantAPITestCase;TestCase | 11 | Dashboard metricas endpoint: structure, per-widget data, 401, cache invalidation admin/non-admin. |

### 4.16 `apps/tenant/perfil/tests/`, `apps/tenant/bancos/tests/` (6 files total, 5 tests)

| File | Base class | # | Summary |
|---|---|---|---|
| perfil/test_models.py | TenantTestCase | 1 | Create TenantProfile + unique_together constraint. |
| perfil/test_organizational_context_adoption.py | SintelTenantTestCase | 2 | PerfilViewSet organizational-context SSOT adoption. |
| perfil/test_tabla_view.py | (pytest) | 1 | Tabla perfiles hides delete button on own row. |
| bancos/test_cross_tenant_isolation.py | (pytest) | 2 | JWT from one tenant can't read another tenant's bancos data. |
| bancos/test_multitenant_isolation.py | (pytest) | 1 | Bancos tabla HTML multitenant isolation. |
| bancos/test_organizational_context_adoption.py | SintelTenantTestCase | 1 | CuentaBancariaViewSet organizational-context SSOT adoption. |

### 4.17 `apps/public/` (13 files, 92 tests)

| File | Base class | # | Summary |
|---|---|---|---|
| accounts/test_api_accounts.py | PublicAPITestCase | 12 | User CRUD API, me endpoint, filter/search, admin-required. |
| accounts/test_templates.py | PublicAPITestCase | 2 | API endpoints don't render templates. |
| console/test_api_views.py | PublicAPITestCase (x9) | 41 | Console DataTables API: staff-only, draw echo, search/pagination, tenant CRUD via console (largest file in apps/ by test count). |
| console/test_views.py | TestCase (x4) | 15 | Console page views: anon redirect, non-staff 403, staff 200 + context, across multiple console pages. |
| core/test_email_service.py | TestCase | 4 | Invitation/password-reset email dispatch (async task + sync send). |
| core/test_public_index_view.py | TestCase | 4 | Public index routing by user state (anon/staff/tenant-member/no-membership). |
| core/test_session_security.py | TestCase | 3 | Session security: clean session, suspicious UA alerting. |
| impuestos/test_api_impuestos.py | PublicAPITestCase (x5) | 12 | Tipos/tarifas/conceptos/codigos/actividades read API, write blocked (405). |
| impuestos/test_api_ingesta.py | PublicAPITestCase | 7 | Ingesta document API: file/url create, mutual exclusion, hash calc, auth required. |
| impuestos/test_templates.py | PublicAPITestCase | 1 | API endpoints don't render templates. |
| tenants/test_api_tenants.py | PublicAPITestCase (x2) | 13 | Tenants/domains read API, writes blocked (405), filter/search/pagination. |
| tenants/test_core_onboarding_flow.py | (pytest) | 1 | Onboarding one-time-token cookie flow. |
| tenants/test_templates.py | PublicAPITestCase | 2 | API endpoints don't render templates. |

### 4.18 `tests/tenant/core/` (46 files, 265 tests — largest single directory in the repo)

Given the size (46 files), full one-line-per-file detail is provided but
grouped; individual test names were sampled rather than exhaustively read
for every file (all counts/classes are exact/grepped, not estimated).

**`smoke/` subdir (20 files):** boot-sequence CLI-arg shape checks (2),
core API/auth/landing/modules/orchestration smoke against the tenant core
app (8), dashboard-sections structure (1), full E2E flow console→tenant
(2), link-registry no-hardcodes checks (2), migrate-schemas CLI shape (1),
perfil-core API smoke (1), UI-contract JSON-only checks (1), and
workspace/mailinbox/activos-fijos static-template smoke (4). All 20 use
`SintelTenantTestCase` except `test_e2e_full_flow.py`/
`test_e2e_workspace_verification.py` (plain `TestCase`),
`test_workspace_empresa_integridad.py`/`test_workspace_empresa_modules_smoke.py`
(raw `TenantTestCase` — contamination-risk, see §2a), and
`test_workspace_activos_fijos_move.py` (`SimpleTestCase`, no DB).

**non-`smoke/` (26 files):** admin-site integration (`TenantTestCase`,
contamination-risk), branding-agnostic checks, core API parity with the
smoke version above, auth/landing/compositor/shell-routes smoke variants
(6 more `*_smoke.py` files that overlap the `smoke/` subdir's coverage of
the same core endpoints — itself a dedup candidate worth a follow-up pass
outside facturas), orchestrator empresa-payload/mail-inbox tests, password-
reset facade smoke (2 near-duplicate files:
`test_password_reset_core_facade_smoke.py` vs
`test_password_reset_facade_smoke.py`), routing logic, template structure,
tenant admin site, and 9 `test_workspace_*.py` files covering the workspace
shell UI (account dropdown, CRUD integration — raw `TenantTestCase`,
contamination-risk — dashboard/landing integration, logout API,
navigation, routing auth, smoke E2E, UI structure).

**Flag for follow-up (outside facturas, noted per the task's request to
flag anything obviously overlapping):** `tests/tenant/core/smoke/test_core_api_smoke.py`
and `tests/tenant/core/test_core_api.py` have near-identical test names
(`dashboard_200`/`core_dashboard_endpoint`, `mi_empresa_200`/`mi_empresa_endpoint`,
`facturas_resumen_200`/`facturas_resumen_endpoint`) against what looks like
the same core API — a second strong duplicate cluster comparable in shape
to the facturas upload-UBL one in §3a.

### 4.19 `tests/public/tenants/` (39 files, ~360 tests — second largest directory)

Too large for a full per-file table entry each with a distinct summary
without reading every file; the file list and hard counts (base class,
`def test_` count) were captured for all 39 files via grep and are
accurate, but summaries below are grouped by theme rather than one bespoke
line per file, per the "honest about scale" instruction.

Themes present (all pytest-style except `test_auth_backend.py` and
`test_domain_activation.py`, which are `TestCase`/`TenantTestCase`
respectively): tenant CRUD via admin/API/console (`test_admin_*`,
`test_api*`, `test_crud_full.py` — 24 tests, `test_console_pages.py`),
domain normalization/validation (`test_domain_*.py` — 4 files), onboarding
flow variants (`test_onboard*.py` — 9 files covering async task,
invitation, resilience, username edge cases, no-password policy —
substantial internal overlap in "onboard creates X" assertions across
these 9 files, flagged for a dedicated pass), deletion/hard-delete rules
(`test_delete_*.py`, `test_hard_delete_*.py`, `test_deletion.py` — 7 files,
also mutually overlapping on "cannot delete active/public tenant"
assertions), suspension/toggle-active (`test_tenant_suspension.py`,
`test_toggle_active.py`), migrate-schemas invocation shape (`test_migrate_*.py`
— 2 files, similar to the celery duplicate in §3g), models (`test_models.py`,
17 tests), tasks (`test_tasks.py`, 12 tests), and integrity/public-tenant
protection (`test_integrity.py`, `test_public_tenant_protection.py`).

### 4.20 `tests/tenant/landing/` (20 files, ~99 tests) and `tests/tenant/empresa/` (19 files, ~87 tests)

Both fully enumerated in the raw grep data (file/class/count captured for
all 39 files across the two dirs). Landing: activation-flow variants
(`test_activate_owner.py`, `test_activate_una_sola_vez.py`,
`test_activation_409.py`, `test_activation_api.py`,
`test_activation_dev_flow.py`, `test_activation_flow_v2_29.py` — 6 files
all asserting overlapping activate-token-once/invalid-token/mismatch
behavior, a third duplicate cluster worth flagging for follow-up),
login/logout/password-reset (`test_login_*.py` x3, `test_logout_api_smoke.py`,
`test_password_reset_*.py` x2), landing API/architecture/routing
(`test_landing_*.py` x5, `test_public_api.py`, `test_private_routing.py`,
`test_routing_guarantee.py`). Empresa: singleton CRUD (`test_empresa_singleton_api.py`,
`test_empresa_singleton_db.py`, `test_empresa_create_update_smoke.py`,
`test_empresa_crud.py`, `test_empresa_api.py` — 5 files with meaningful
overlap on "create returns 409 if exists"), mailinbox config
(`test_mailinbox_*.py` x3), modales/page/template smoke (4 files), and
SSOT/logic (`test_empresa_ssoT.py`, `test_empresa_logic.py`).

### 4.21 Remaining `tests/tenant/*` domains (dashboard 8, security 7, critical 6, inventario 4, perfil 3, gastos 3, bancos 3, empleados 2, contabilidad 1, compras 1 — 38 files total)

All captured with exact base class + test count in the raw data; one-line
summaries:

| File | Base class | # | Summary |
|---|---|---|---|
| dashboard/test_access.py | SintelTenantTestCase | 5 | Access control: anon redirect, cross-tenant denied, membership-gated API. |
| dashboard/test_api_first_compliance.py | SintelTenantTestCase | 5 | Dashboard is API-first: no hardcoded branding, no dashboard-owned URLs. |
| dashboard/test_api_first_guards.py | TestCase | 5 | Static guard: no template views/render calls/templates in dashboard app. |
| dashboard/test_dashboard_api.py | SintelTenantTestCase (x5) | 12 | Summary/KPIs/quick-actions endpoints, role filtering, inactive-membership denial. |
| dashboard/test_dashboard_api_smoke.py | SintelTenantTestCase | 2 | Dashboard data smoke + auth required. |
| dashboard/test_dashboard_partials_smoke.py | SintelTenantTestCase | 5 | Header/KPIs/charts/table partials return 200. |
| dashboard/test_role_redirect_integration.py | SintelTenantTestCase (x4) | 11 | Role-based post-login redirect (admin/staff/user) via page and API. |
| dashboard/test_shell_apifirst.py | TestCase | 6 | Dashboard shell consumes core API, no inline scripts/absolute URLs. |
| security/test_cross_tenant.py | (pytest) | 2 | User cannot access another tenant's domain. |
| security/test_csrf_required.py | (pytest) | 2 | POST without CSRF forbidden, with CSRF allowed. |
| security/test_full_integration.py | SintelTenantTestCase | 5 | Numbered end-to-end: API backend barrier, UX feedback, happy path, public-tenant protection, cross-check isolation. |
| security/test_host_header.py | (pytest) | 2 | Invalid/valid Host header handling. |
| security/test_isolation.py | TenantTestCase | 6 | Cross-tenant view/API access denied, data leak check (contamination-risk, §2a). |
| security/test_norma_exposicion_datos.py | SintelTenantTestCase | 9 | Data-exposure norms: facturas/asientos/cuentas/empresa list vs detail serializer field minimality. |
| security/test_url_isolation.py | SintelTenantTestCase | 9 | Console/public-API/admin-API routes return 404 on private tenant domains. |
| critical/test_auth_authorization.py | TenantTestCase (x2) | 4 | Login valid/invalid, permission-restricted modules, middleware active per request (contamination-risk, §2a). |
| critical/test_critical_errors.py | TestCase (x2) | 5 | Nonexistent domain, deactivated tenant, missing schema, no tenant context, no crash on expected errors. |
| critical/test_data_isolation.py | TenantTestCase | 4 | Tenant A can't see tenant B data; direct-ID access impossible (contamination-risk, §2a). |
| critical/test_functional_basic.py | TenantTestCase (x3) | 6 | Basic CRUD smoke: crear/listar/eliminar factura, crear/listar cliente, crear empresa singleton (contamination-risk, §2a). |
| critical/test_startup_availability.py | TestCase | 6 | Migrations run, server starts, tenant access works, healthcheck available. |
| critical/test_tenant_onboarding.py | TestCase | 6 | Full tenant creation: schema, domain resolution, admin login, no impact on existing tenants, idempotency. |
| inventario/test_crud_permissions.py | mixed (InventarioPermissionsMixin, SintelTenantTestCase x3) | 16 | Role-based CRUD permission matrix for productos/activos/movimientos. |
| inventario/test_inventario_materialization.py | TenantTestCase | 3 | Materialize-from-DTO: missing fields, invalid type (contamination-risk, §2a). |
| inventario/test_inventario_parser_integration.py | (pytest) | 2 | CSV/Excel inventario parsing. |
| inventario/test_inventario_validator.py | (pytest) | 3 | Validator: ok, no items, invalid date. |
| perfil/smoke/test_perfil_endpoints.py | (pytest) | 5 | Perfil `me` endpoint GET/PATCH json/multipart/configuracion, 404 from public domain. |
| perfil/test_perfil.py | SintelTenantTestCase (x3) | 7 | Perfil service-layer CRUD, `me` endpoint consumption, cross-tenant isolation. |
| perfil/test_perfil_api.py | SintelTenantTestCase | 6 | `me` endpoint auth/CSRF/configuracion normalization. |
| gastos/test_gasto_materialization.py | TenantTestCase | 4 | Materialize-from-DTO: missing number/fields, invalid total (contamination-risk, §2a). |
| gastos/test_gasto_parser_integration.py | (pytest) | 2 | CSV/TXT gasto parsing. |
| gastos/test_gasto_validator.py | (pytest) | 5 | Validator: ok, total zero/negative, invalid date, missing total. |
| bancos/test_cuenta_bancaria_crud.py | SintelTenantTestCase | 4 | Create/edit/delete via service + API flow. |
| bancos/test_extracto_bancario_crud.py | SintelTenantTestCase | 4 | Create extracto, ETL processing, invalid Excel handling. |
| bancos/test_multitenant_isolation.py | SintelTenantTestCase | 3 | 3-level isolation: query, write/IDOR, cross-talk. |
| empleados/smoke/test_templates_exist.py | SimpleTestCase | 5 | Template existence checks (list/create/edit/assets). |
| empleados/test_endpoint_after_login.py | (pytest) | 3 | Endpoint 401/200/403 by auth+membership state. |
| contabilidad/test_conta_min.py | SintelTenantTestCase | 2 | Minimal cuentas/asientos endpoint 200 checks. |
| compras/test_compras_plantillas.py | SintelTenantTestCase | 5 | Plantilla CRUD, order-from-plantilla, rango-excedido/no-vigente rejection, tenant isolation. |

### 4.22 `tests/public/impuestos/` (13 files, ~91 tests), `tests/public/console/` (6 files, ~42 tests), `tests/public/accounts/` (3 files, 15 tests), `tests/public/shared/` (1 file, 4 tests)

| File | Base class | # | Summary |
|---|---|---|---|
| impuestos/test_api_readonly.py | (pytest) | 7 | Read-only public API: tipos/tarifas/conceptos/normas, write blocked. |
| impuestos/test_crud_tipos.py | (pytest) | 6 | Full CRUD via API for tipo, incl. auth requirement. |
| impuestos/test_datatables_tipos.py | (pytest) | 5 | DataTables endpoint: basic/pagination/search/order/auth. |
| impuestos/test_etl_pipeline.py | (pytest) | 4 | ETL: CSV creates normas, atomicity on error, HTML processing, stats. |
| impuestos/test_ingesta_api.py | (pytest) | 5 | Ingesta: multipart CSV, URL+robots, throttling, idempotency by hash. |
| impuestos/test_ingesta_e2e.py | (pytest) | 12 | Full ingesta E2E incl. CSRF, content-type variants, console flow. |
| impuestos/test_links_templates.py | (pytest) | 8 | Console impuestos pages return 200 / 404 appropriately. |
| impuestos/test_normativa_dian_api.py | TestCase | 10 | DIAN normativa catalogs: contribuyente/regimen/responsabilidad/perfil tributario. |
| impuestos/test_ops_health.py | (pytest) | 6 | Ops: health endpoint, reindex/seed/smoke/export commands. |
| impuestos/test_provider.py | TestCase | 10 | Provider functions: regimen/responsabilidades/perfil lookups + cache invalidation. |
| impuestos/test_provider_form_metadata.py | (pytest) | 4 | Form-metadata smoke, CIIU lookup. |
| impuestos/test_queries_perf.py | TestCase | 3 | N+1 query guard on listado/detalle endpoints. |
| impuestos/test_search_api.py | (pytest) | 4 | Search endpoint, highlight, pagination, throttling. |
| console/test_console_api.py | (pytest) | 8 | Tenants/domains/users DataTables API, health endpoint. |
| console/test_jwt_e2e.py | (pytest) | 12 | Full JWT lifecycle: obtain/refresh/verify, session-JWT bridging. |
| console/test_resend_owner_activation.py | (pytest) | 7 | Resend-activation: 200/409/429/404 states, dry-run. |
| console/test_tenant_ui_flow.py | (pytest) | 12 | Tenant-creation UI flow incl. validation, domain, signal-created domain. |
| console/test_tenants_column_domain.py | (pytest) | 4 | DataTables tenants column shows correct primary domain. |
| console/test_users_dt.py | (pytest) | 1 | Console users DataTables smoke. |
| accounts/test_admin_users_list.py | (pytest) | 3 | Admin users list requires admin, pagination. |
| accounts/test_user_crud_api.py | (pytest) | 7 | User CRUD via API: create/list/update/delete, duplicate email. |
| accounts/test_users_create.py | (pytest) | 5 | Create-user edge cases: mismatch, duplicate, missing password2, too-short. |
| shared/test_datatable_helper.py | (pytest) | 4 | DataTable helper importable, spec/server creation. |

**Note:** `accounts/test_admin_users_list.py`, `accounts/test_user_crud_api.py`
and `apps/public/accounts/tests/test_api_accounts.py` (§4.17) plausibly
overlap on user-CRUD-via-API coverage across the apps/ vs tests/ split, same
pattern as facturas — flagged for a broader (non-facturas) follow-up.

### 4.23 `tests/services/` (14 files, 62 tests)

| File | Base class | # | Summary |
|---|---|---|---|
| document_ingest/test_ingest_router.py | (pytest) | 3 | Routes document to parser by type/mime. |
| document_ingest/test_ingest_service_persist.py | (pytest) | 2 | Persist invoice + idempotency. |
| document_ingest/test_ingest_service_preview.py | (pytest) | 2 | Preview XML invoice, invalid document. |
| document_ingest/test_ingest_validators.py | (pytest) | 9 | Validators for factura/creditnote/gasto/inventario, missing-field cases. |
| document_parser/test_csv_parser.py | (pytest) | 2 | CSV parsing basic + gasto variant. |
| document_parser/test_detector.py | (pytest) | 10 | File-type detection: magic bytes, extension, mime, content heuristics. |
| document_parser/test_excel_parser.py | (pytest) | 2 | XLSX/XLS invoice parsing. |
| document_parser/test_normalizer.py | (pytest) | 10 | Encoding/whitespace/accent/numeric/NIT/currency normalization. |
| document_parser/test_pdf_parser.py | (pytest) | 2 | PDF invoice/creditnote parsing. |
| document_parser/test_txt_parser.py | (pytest) | 1 | TXT basic parsing. |
| document_parser/test_xml_parser.py | (pytest) | 3 | UBL 2.1 invoice/creditnote parsing, invalid XML. |
| maildigester/test_detectors_contract.py | (pytest) | 8 | File-kind guessing, XML extraction from AttachedDocument, UBL invoice detection. |
| maildigester/test_pipeline_contract.py | (pytest) | 4 | Collect invoice XML from mailbox, DTO shape, custom client, empty mailbox. |
| maildigester/test_tasks.py | (pytest) | 3 | fetch_and_process_billing_mail: eager, validation error, empty mailbox. |

### 4.24 Remaining small `tests/` top-level dirs (13 files)

| File | Base class | # | Summary |
|---|---|---|---|
| api/test_upload_document_endpoint_gasto.py | TenantTestCase | 5 | Gasto document upload: preview, missing file, invalid total, response shape, json-only (contamination-risk, §2a). |
| api/test_upload_document_endpoint_inventario.py | TenantTestCase | 2 | Inventario document upload: preview, no items (contamination-risk, §2a). |
| celery/test_tasks_import.py | (pytest) | 3 | Celery task import/autodiscovery smoke — **byte-identical to celery_tasks/test_tasks_import.py**, see §3g. |
| celery_tasks/test_tasks_import.py | (pytest) | 3 | Same as above — **byte-identical duplicate**, see §3g. |
| core/test_middleware_imports.py | (pytest) | 1 | Middleware path importable. |
| core/test_routing_architecture.py | (pytest) | 10 | Public/tenant URLconf separation across many route classes. |
| docker/test_docker.py | unittest.TestCase (x4) | 7 | Dockerfile lint, compose build, migrations command, container structure (shells out to Docker). |
| e2e/test_facturas_workspace.py | (pytest) | 4 | Facturas workspace UI: upload xml, missing-file error, view detail, delete. |
| e2e/test_workspace_facturas_forensics.py | (pytest) | 2 | Workspace upload/detail/delete forensics — overlaps test_facturas_workspace.py. |
| general/test_system_health.py | SintelTenantTestCase | 4 | Public health, tenant lifecycle, private access, subdomain strictness. |
| multitenant/test_cross_tenant_isolation.py | TenantTestCase | 1 | Document isolation between tenants (contamination-risk, §2a). |
| multitenant/test_tenant_routing_upload_document.py | TenantTestCase | 2 | Upload uses current tenant schema; endpoint available in tenant urlconf (contamination-risk, §2a). |
| routing/test_public_vs_tenant_urlconf.py | (pytest) | 6 | Public console vs tenant landing/API route exposure by host. |
| smoke/test_logging_mailinbox.py | (pytest) | 2 | Mailinbox logger exists + has handlers. |
| tenant_auth/test_no_redirect_loop.py | (pytest) | 4 | No login-page redirect loop; static/public bypass membership check. |
| tenant_auth/test_public_tenant_access.py | (pytest) | 7 | Public tenant root/admin not forbidden; well-known/static/media paths not blocked. |
| tenant_routing/test_admin_disabled_on_tenants.py | (pytest) | 4 | Admin not exposed on tenant domains; root lands on tenant index. |

---

## 5. Support/helper files (not counted as tests)

Excluded from the 389 test-file count and from all test-function totals:

**`apps/**/tests/` (20 files):** `apps/config/tests/base_public.py`,
`apps/config/tests/base_tenant.py`, `apps/public/console/tests/conftest.py`,
`apps/tenant/api/tests/base.py`, `apps/tenant/core/tests/base_test.py`, plus
one `conftest.py` each in bancos, clientes, compras, contabilidad,
cotizaciones, empleados, empresa, facturas, gastos, inventario, perfil,
proveedores, proyectos, ventas, and `apps/tenant/cotizaciones/tests/factories.py`.

**`tests/**` (7 files):** `tests/tenant/base_test.py` (defines
`SintelTenantTestCase` — the preferred base class per §2),
`tests/public/impuestos/factories.py`, `tests/public/tenants/factories.py`,
and 4 `conftest.py` files.

---

## 6. Open questions for the dedup/removal phase (not answered here by design)

1. Does `TenantAPITestCase` (13 files) wrap `SintelTenantTestCase` or raw
   `TenantTestCase` internally? If the latter, the contamination-risk count
   in §2 is undercounted by up to 13 files.
2. For each duplicate cluster in §3, which file is the one to keep — the
   most recent, the most complete, or the one with the clearest name? Not
   judged here per the task's explicit scope boundary.
3. `tests/tenant/core/` (46 files) and `tests/public/tenants/` (39 files)
   have internal overlap clusters flagged in §4.18-4.20 that were not
   individually evidenced to the same test-name-collision depth as the
   facturas section — worth a dedicated inventory pass each before any
   dedup action there.
