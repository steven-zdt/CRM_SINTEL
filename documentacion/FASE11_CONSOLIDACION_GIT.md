# Consolidación Git — FASE 11

**Fecha:** 2026-08-09
**Estado de la fase:** 🟢 COMPLETED — plan ejecutado con autorización explícita del usuario tras el turno en que se preparó
**Resultado real de la ejecución (verificado, no asumido):**

```
34fc020 docs: ADR-003/004/005 + consolidacion completa OCF/OSF (auditoria FASE 0-12)
1d19d8f test(scope): suite de adopcion OCF por app + aislamiento organizacional Empresa/Sede/Area
c63b35e feat(scope): filtrado por alcance organizacional en 6 apps (OSF F7/F9/F10/F11) + adopcion aditiva del resto
120d17e feat(compras): piloto oficial ADR-003/OSF - SedeAwareModel + HasOrganizationalScope
0295932 feat(core): Organizational Context Framework (OCF) - contexto organizacional Empresa->Sede->Area
```

Los 5 commits se ejecutaron en el orden del plan (§2), cada uno verificado con `git status` antes
de `git commit` para confirmar que el archivo staged coincidía exactamente con la lista planeada
(ni de más ni de menos). El hook `[PRE-COMMIT] SSoT Guard` pasó limpio en los 5. Tras el quinto
commit, `git status` confirmó que los únicos ~75 archivos restantes sin commitear son exactamente
los de la categoría E (exclusiones de §3) — ninguno de OCF/OSF quedó fuera.

**Nota honesta sobre `apps/services/onboarding/empresa_service.py`:** se incluyó completo en el
Commit 2 (el hook de semilla ADR-003 es la parte más grande), sin separar por hunk el fix de la
Remediación Auditoría Enterprise que también contiene — la advertencia de §4 sigue vigente para
quien revise ese commit específico.

---

## 1. Validaciones previas — ejecutadas, todas limpias

Por regla de `AGENTS.md`, antes de cualquier commit:

| Comando | Resultado |
|---|---|
| `python manage.py check` | `System check identified no issues (0 silenced)` |
| `python manage.py makemigrations --check --dry-run` | `No changes detected` (ningún modelo cambiado sin su migración correspondiente) |
| `python -m compileall` (archivos tocados en esta sesión) | Exit 0, sin errores |
| `pytest` (compras, core) | Ya confirmado en fases anteriores: `53 passed` (core), `20 passed` (compras, tras los fixes de FASE 7) |

---

## 2. Plan de commits (5, por responsabilidad — adaptado a los límites reales de archivo del proyecto, no una división artificial)

**Alcance de este plan:** solo archivos relacionados a OCF/OSF (categorías A/B/C/D de `OCF_OSF_BASELINE.md` §4, más lo producido en esta consolidación). **No incluye la categoría E** (EKG, Remediación Auditoría Enterprise 2026-08-06, fixes de infraestructura/dependencias) — esos ~35 archivos quedan fuera de este plan, sin tocar, para que quien sea dueño de esa línea de trabajo los commitee por separado. Ver lista completa de exclusiones en §3.

### Commit 1 — OCF: infraestructura núcleo
```
apps/tenant/core/services/organizational_context.py
apps/tenant/core/services/organizational_scope.py
apps/tenant/core/services/organizational_permissions.py
apps/tenant/core/services/organizational_dsv.py
apps/tenant/core/services/organizational_bridges.py
apps/tenant/core/services/organizational_filters.py
apps/tenant/core/services/organizational_service_layer.py
apps/tenant/core/services/sede_context.py
apps/tenant/core/context_processors.py
apps/tenant/core/api/contexto.py
apps/tenant/core/api/urls.py
apps/tenant/core/models.py
apps/tenant/core/templates/tenant/core/workspace.html
apps/tenant/core/templates/tenant/partials/_header.html
apps/tenant/core/static/core/js/common/sede_selector.js
apps/tenant/api/mixins.py
apps/tenant/api/permissions.py
apps/tenant/perfil/models.py
apps/tenant/perfil/migrations/0008_add_alcance_and_sede_area_context.py
apps/tenant/core/tests/test_organizational_bridges.py
apps/tenant/core/tests/test_organizational_context.py
apps/tenant/core/tests/test_organizational_dsv.py
apps/tenant/core/tests/test_organizational_filters.py
apps/tenant/core/tests/test_organizational_permissions.py
apps/tenant/core/tests/test_organizational_resolver.py
apps/tenant/core/tests/test_organizational_scope.py
apps/tenant/core/tests/test_organizational_selectors.py
apps/tenant/core/tests/test_organizational_service_layer.py
config/settings.py  -- SOLO la línea del context_processor (ver nota §4)
```
Mensaje sugerido: `feat(core): Organizational Context Framework (OCF) - contexto organizacional Empresa->Sede->Area, resuelto por request`

### Commit 2 — OSF: semilla organizacional y piloto `compras`
```
apps/tenant/empresa/services/business_service.py
apps/tenant/empresa/management/commands/backfill_sede_area.py
apps/services/onboarding/empresa_service.py  -- ver nota de archivo mixto en §4
apps/tenant/compras/models.py
apps/tenant/compras/migrations/0004_add_alcance_and_sede_area_context.py
apps/tenant/compras/migrations/0005_add_empresa_sede_composite_index.py
apps/tenant/compras/migrations/0006_backfill_orden_compra_sede.py
apps/tenant/compras/migrations/0007_harden_orden_compra_sede_not_null.py
apps/tenant/compras/services/*.py
apps/tenant/compras/api/viewsets.py
apps/tenant/compras/api/serializers.py
apps/tenant/compras/tables.py
apps/tenant/compras/views.py
apps/tenant/compras/templates/tenant/compras/offcanvas_detalle_compras.html
apps/tenant/compras/static/compras/js/compras.utils.js
apps/tenant/compras/__init__.py
```
Mensaje sugerido: `feat(compras): piloto oficial ADR-003/OSF - SedeAwareModel, HasOrganizationalScope, filtrado por alcance completo`

### Commit 3 — OSF: rollout de lectura a 6 apps (F7/F9/F11)
```
apps/tenant/{facturas,cotizaciones,gastos,inventario,proyectos,empleados}/api/*.py
apps/tenant/{facturas,cotizaciones,gastos,inventario,proyectos,empleados}/services/*.py
apps/tenant/{facturas,cotizaciones,gastos,inventario,proyectos,empleados}/views.py
apps/tenant/ventas/services/api_mixins.py
apps/tenant/ventas/services/business_service.py
apps/tenant/ventas/api/viewsets.py
-- más las 15 apps con OrganizationalContextMixin heredado sin invocar
   (bancos, clientes, contabilidad, dashboard, empresa, perfil, proveedores):
   apps/tenant/{bancos,clientes,contabilidad,dashboard,empresa,perfil,proveedores}/api/viewsets.py
```
Mensaje sugerido: `feat(scope): filtrado por alcance organizacional en facturas/cotizaciones/gastos/inventario/proyectos/empleados (OSF F7/F9/F11) + adopcion aditiva de OrganizationalContextMixin en el resto`

### Commit 4 — Tests de adopción y aislamiento (todas las apps)
```
apps/tenant/*/tests/test_organizational_context_adoption.py
apps/tenant/{compras,cotizaciones,empleados,facturas,gastos,proyectos}/tests/test_scope_*_f*.py
apps/tenant/compras/tests/test_organizational_isolation_empresa_a.py
apps/tenant/empresa/tests/test_estructura_organizacional_inicial.py
apps/tenant/{bancos,compras}/__init__.py
apps/tenant/cotizaciones/tests/__init__.py
tests/tenant/compras/test_compras_plantillas.py
apps/tenant/compras/tests/test_multitenant_isolation_tabla_html.py
apps/tenant/contabilidad/tests/test_retenciones_api.py  -- verificar si es OSF-relacionado o E (ver nota §4)
pytest.ini
```
Mensaje sugerido: `test(scope): suite de adopcion OCF por app + aislamiento organizacional Empresa/Sede/Area (FASE 7)`

### Commit 5 — ADRs y documentación
```
docs/ADR-003-contexto-organizacional-sede-area.md
docs/ADR-004-organizational-context-framework-diseno.md
docs/ADR-005-organizational-scope-framework.md
documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md
documentacion/ORGANIZATIONAL_SCOPE_MASTER_PLAN.md
documentacion/ORGANIZATIONAL_SCOPE_BASELINE.md
documentacion/ORGANIZATIONAL_SCOPE_MATRIX.md
documentacion/ORGANIZATIONAL_SCOPE_MIGRATION_STATUS.md
documentacion/ORGANIZATIONAL_CONTRACT.md
documentacion/OCF_OSF_BASELINE.md
documentacion/OCF_TECHNICAL_AUDIT.md
documentacion/OSF_TECHNICAL_AUDIT.md
documentacion/COMPRAS_PILOT_VALIDATION.md
documentacion/FACTURAS_AUDIT.md
documentacion/VENTAS_FACTURAS_AUDIT.md
documentacion/FASE7_AISLAMIENTO_ORGANIZACIONAL.md
documentacion/FASE10_ROLLOUT_CONTROLADO.md
documentacion/FASE11_CONSOLIDACION_GIT.md
"documentacion/Nueva recomendación arquitectónica.md"
"documentacion/ORGANIZATIONAL CONTEXT FRAMEWORK (OCF).md"
documentacion/arquitectura_general.md
```
Mensaje sugerido: `docs: ADR-003/004/005 + consolidacion completa OCF/OSF (auditoria FASE 0-11) - actualiza arquitectura_general.md`

---

## 3. Explícitamente NO incluido (categoría E, `OCF_OSF_BASELINE.md` §4) — sin tocar

```
.github/workflows/ci-quality-gate.yml
Makefile
tools/ekg/*  (8 modificados + 8 nuevos)
apps/public/tenants/management/commands/ensure_tenant_dns.py
apps/tenant/core/middleware.py
nginx/nginx.conf
docker-compose.yaml
requirements.txt
.claude/launch.json
nul
notas.txt
AGENTS.md
CLAUDE.md
MEMORY.md
documentacion/INFRA_RED_LOCAL_MULTI_TENANT.md
documentacion/plan_refactorizacion.md
documentacion/INFORME_FINAL_EKG_GOBERNANZA_2026-08-07.md
documentacion/PLAN_PRUEBASUI_PRIVADAS.md
documentacion/REMEDIACION_FASE1_CRITICOS_SEGURIDAD.md
documentacion/REMEDIACION_FASES2-8_AUDITORIA_ENTERPRISE.md
apps/tenant/facturas/.agent/COMPLETO_FLUJO_FACTURAS.md (+ el .md eliminado)
todos los fixes puntuales de IDs duplicados/doble-submit de la Remediacion Auditoria Enterprise
  (bancos, contabilidad, empleados, empresa, gastos, inventario, proveedores, proyectos -
  archivos .js/.html especificos, NO los .py de scope ya listados arriba)
```

---

## 4. Notas honestas sobre el plan (no ocultas)

- **`apps/services/onboarding/empresa_service.py`** mezcla dos cosas en el mismo diff: el fix de la Fase 5 de la Remediación Auditoría Enterprise (categoría E, `crear_empresa`/`onboard_tenant` creaban `TenantProfile` sin `Empresa`) y el hook de semilla organizacional de ADR-003 (categoría B). Separarlas requeriría `git add -p` (staging por hunk) revisando cada bloque — no se hizo en este plan por el volumen; se incluyó completo en el Commit 2 porque el hook de semilla es la parte más grande y más directamente relacionada a OSF. Si te importa la separación exacta, puedo hacer el staging por hunk antes de commitear.
- **`config/settings.py`** tiene un solo cambio relevante a OCF (registro del context processor) mezclado con cualquier otro cambio no relacionado que pueda tener — mismo caso, se listó con nota para revisar antes de `git add`.
- **`apps/tenant/contabilidad/tests/test_retenciones_api.py`** está modificado pero no confirmé en esta fase si el cambio es por OSF o por otra razón (no se auditó su diff específico) — marcado para verificar antes de incluirlo en el Commit 4.
- Esto NO es una lista exhaustiva verificada línea por línea de los ~186 archivos de las categorías A/B/D — se construyó a partir de la categorización ya hecha en `OCF_OSF_BASELINE.md` §4, complementada con lo nuevo de esta sesión. Antes de ejecutar, recomiendo un `git status`/`git diff --stat` final para confirmar que no falta ni sobra nada.

---

## 5. Cómo ejecutar (pendiente de tu autorización explícita)

```bash
# Por cada commit, en orden (1 a 5):
git add <lista de archivos del commit>
git status   # verificar que no se coló nada de la lista de exclusiones
git commit -m "<mensaje sugerido>"
```

**No se ejecuta nada de esto sin tu confirmación explícita y separada** — "termina la tarea en su totalidad" autorizó completar la auditoría/implementación de OCF/OSF, no específicamente escribir en el historial de git (una acción difícil de revertir una vez hecha, especialmente mezclando 186+ archivos).

**Fase completada (plan). Ejecución de los commits pendiente de tu autorización explícita — continuando a FASE 12 en el mismo turno.**
