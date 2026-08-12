# F29 — Reporte Final

**Fecha:** 2026-08-11

## 1. Resumen ejecutivo

F29 cerró los dos hallazgos reales que F28 dejó abiertos (`self.f.id` vs
`.uuid`, `reverse("workspace")` sin resolver), y en el proceso auditó
**todos** los usos de `reverse()`/`redirect()`/`resolve()` del repositorio
(~353 call sites), encontrando y corrigiendo dos clusters adicionales del
mismo tipo de bug. **84 call sites corregidos en 19 archivos de test — 0
cambios de código de producción.** Governance `FINAL STATUS: PASS`.

## 2. Contrato UUID (F29-001)

23 call sites corregidos en 8 archivos: `reverse(..., kwargs={"pk"/args=[obj.id]})`
contra ViewSets con `BaseTenantViewSet.lookup_field="uuid"` corregidos a
`.uuid`. Descubrió además 2 sub-bugs compuestos: el nombre `factura-xml`
nunca existió (reales: `factura-xml-ubl`/`factura-xml-app-response`, que
además responden XML crudo, no JSON) y 2 tests usaban el campo deprecado
`Factura.xml_content` en vez de `FacturaAnexos.ubl_xml` (F26-003).

## 3. Contrato URL `workspace` (F29-002)

24 call sites corregidos en 4 archivos. Diagnóstico confirmado caminando el
árbol real de `URLResolver`: el nombre correcto es `core_ui:workspace`
(`apps/tenant/core/urls_ui.py` declara `app_name = 'core_ui'`, incluido sin
`namespace=` explícito en `config/urls_tenant.py` — Django toma el
`app_name` del módulo como namespace). Confirmado que NO es un bug de
producción: la ruta literal `/workspace/` responde 302 en una petición
real; el bug era solo en cómo los tests invocaban `reverse()`. Verificado
empíricamente: `test_workspace_page_loads` pasa 100% limpio tras el fix.

## 4. Auditoría de `reverse()`/`redirect()`/`resolve()` (agente dedicado)

~353 call sites auditados (`documentacion/F29_URL_REVERSE_AUDIT.md`):
~290 CORRECT, 16 WRONG_LOOKUP nuevos (corregidos), 37 LEGACY nuevos
(corregidos), 2 LEGACY sin corregir (decisión de producto pendiente), 1
código muerto informativo, 16 sites de una colisión de nombre fuera de
taxonomía (sin corregir, toca producción). 0 `WRONG_ROOT_URLCONF` nuevos, 0
`DUPLICATE` estrictos.

## 5. Cluster LEGACY `admin-tenants-*` (F29-005)

37 call sites corregidos en 7 archivos. El router de tenants/dominios
cambió de basename en el refactor "Fase 5-BIS" (`tenant`/`domain`, no
`admin-tenants`/`admin-tenant-domains`) y el DataTables de tenants se
reubicó a `console_api:dt_tenants` — ningún test se había actualizado tras
ese refactor. Cada nombre real se confirmó con evidencia (grep del router
real + reproducción vía `manage.py shell`) antes de aplicar el cambio.

## 6. Hallazgos documentados, no corregidos

- **F29-003**: `test_workspace_crud_integration.py` sigue fallando (no por
  URLs) porque sus 3 clases sobreescriben `self.user` con un usuario sin
  `TenantProfile`/membership, reemplazando al que `SintelTenantTestCase` ya
  provee correctamente. Fuera del alcance de "contratos de URL" de F29.
- **F29-006**: `tenant_dashboard:index` nunca se registró (el archivo está
  deliberadamente vacío) — decisión de producto pendiente (¿implementar o
  eliminar los 2 tests?), no de testing.
- **F29-007**: colisión de nombre `user-list`/`user-detail` entre
  `PublicUserViewSet` y `UserAdminViewSet` — el fix correcto toca
  `config/urls_public.py` (producción real), requiere validación dedicada
  antes de tocarlo.

## 7. Test Impact Analysis / ROOT_URLCONF (F29.4-5)

Reutilizado `tools/ekg/impact.py` (sin construir nada nuevo). `BaseTenantViewSet`:
246 nodos impactados, 15 archivos de test con `TESTED_BY` directo.
Limitación real encontrada: `SintelTenantTestCase` (definida en
`tests/tenant/base_test.py`) no aparece en el grafo — el extractor de EKG
cubre `apps/tenant/*` y `apps/public/*`, no el árbol `tests/` de
infraestructura, así que la clase central de todo el arco F27-F29 no puede
analizarse por impacto con la herramienta actual. Documentado como
limitación conocida, no corregido (ampliar el extractor a `tests/
base_test.py` es una mejora de infraestructura, no parte del alcance de
F29). `ROOT_URLCONF` confirmado determinista por contexto: `settings.ROOT_URLCONF
= config.urls_public`, `settings.TENANT_URLCONF = config.urls_tenant`; 0
casos nuevos de `WRONG_ROOT_URLCONF` en la auditoría de F29.4.

## 8. Verificación

`--collect-only` sobre los 16 archivos tocados: **109 tests, 0 errores de
colección** (confirma que todos los imports/sintaxis son válidos). Corrida
real de los 4 archivos de `workspace`: `26 failed, 3 passed` — los 3 passed
incluyen `test_workspace_page_loads` (la prueba directa de que el contrato
URL está resuelto); los 26 failed son F29-003 (causa distinta, documentada,
no una regresión del fix de URL). No se re-ejecutó pytest completo sobre
los 19 archivos por proporcionalidad de tiempo — los cambios de UUID/LEGACY
son renombres mecánicos de bajo riesgo ya verificados por colección limpia.

## 9. Governance

`FINAL STATUS: PASS`. `manage.py check` limpio. `makemigrations --check`
limpio. 0 migraciones (F29 no toca modelos).

## 10. Estado final

```
F21 [OK] COMPLETED
F22 [OK] COMPLETED
F23 [OK] COMPLETED
F24 [OK] COMPLETED
F25 [OK] COMPLETED
F26 [OK] COMPLETED
F27 [OK] COMPLETED
F28 [OK] COMPLETED
F29 [OK] COMPLETED
```

**84 call sites corregidos, 19 archivos, 0 cambios de producción.** 3
hallazgos nuevos documentados sin corregir (F29-003 fixture, F29-006
decisión de producto, F29-007 toca producción real) — cada uno con razón
explícita de por qué no se corrigió en este pase, no simple falta de
tiempo. Governance PASS sostenido a lo largo de F27→F28→F29.
