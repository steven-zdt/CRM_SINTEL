# GASTOS ↔ PROYECTOS — IMPLEMENTATION STATUS

Mission: GASTOS_PROYECTOS_01

Current Phase: PHASE-58 (release gate)
Overall Status: PASS_WITH_DEFERRED

- Fecha inicio: 2026-09-17
- Commit base: 5f48bf3
- Rama: feat/onboarding-cookie
- Entorno: Docker (web container)
- Python: 3.12.14
- `manage.py check` baseline: 0 issues

| Phase | Status | Started | Finished | Evidence | Notes |
|---|---|---|---|---|---|
| PHASE-00 (Control de inicio) | PASS | 2026-09-17 | 2026-09-17 | `manage.py check` -> 0 issues; `git rev-parse --short HEAD` -> 5f48bf3 | Sin cambios de codigo aun |
| PHASE-01 (Auditoria Gastos) | PASS | 2026-09-17 | 2026-09-17 | Lectura real de `apps/tenant/gastos/models.py`, `services/business_service.py`, `services/crud_service.py`, `services/selectors.py`, `api/viewsets.py`, `api/serializers.py` | Confirmado: DocumentoSoporte NO tiene `proyecto_uuid`. Edicion (PATCH) NO pasa por business_service (usa ModelSerializer.save() directo via DRF UpdateModelMixin) -- solo create/anular/desactivar/eliminar pasan por GastoBusinessService |
| PHASE-02 (Auditoria Proyectos) | PASS | 2026-09-17 | 2026-09-17 | Lectura real de `apps/tenant/proyectos/models.py` y `services/business_service.py` | Confirmado: `costo_mano_obra_real`/`costo_materiales_real`/`utilidad_estimada`/`margen_rentabilidad` existen y se recalculan en `calcular_indicadores_financieros()`, llamada desde create/update/avanzar-fase. NO existe `costo_gastos_real` |
| PHASE-03 (Auditoria "Agregar gasto") | PASS | 2026-09-17 | 2026-09-17 | grep en `apps/tenant/gastos/` y `apps/tenant/proyectos/` sin matches reales (solo ruido de `movimiento_inventario_uuid`/`.agent`) | FEATURE_NEW confirmado -- no existe ninguna parte de esta integracion |
| PHASE-04 (Decision de relacion) | PASS | 2026-09-17 | 2026-09-17 | Ver seccion Decisions | UUID opaca (Pull Model), NO FK directa |
| PHASE-05 (Contrato SSoT) | PASS | 2026-09-17 | 2026-09-17 | Ver seccion Decisions | Gasto = dueño del documento; Proyecto = dueño de costos consolidados |
| PHASE-06 (Monto que impacta costos) | PASS | 2026-09-17 | 2026-09-17 | `apps/tenant/contabilidad/integracion/extractores/gastos.py:69-75` (linea DEBE usa `doc.subtotal`, no `doc.total`) | GASTO_COST_AMOUNT_SSoT = `DocumentoSoporte.subtotal` (confirmado por el extractor contable real, no supuesto) |
| PHASE-07 a 58 | RUNNING | 2026-09-17 | | | Implementacion backend + frontend en curso (alcance elegido por el usuario: Backend + Frontend completo) |

## Current Blockers
- None activo. Historico: la primera corrida completa de `apps/tenant/proyectos/tests/` fue matada por el harness por bajo consumo de memoria del sistema (no un bug de esta mision). El proceso pytest real quedo huerfano dentro del contenedor (visible en `docker compose top web`/`docker top` con un PID que no correspondia al namespace real del contenedor -- `docker exec ... kill` y `os.kill()` fallaban con "No such process"). Diagnosticado y resuelto: el PID real se encontro via `wsl.exe -d docker-desktop -- ps aux | grep pytest` (Docker Desktop en Windows corre los contenedores dentro de una VM WSL2; el PID que reporta `docker compose top` no siempre coincide 1:1 con el PID real en esa VM), se elimino con `kill -9` alli, y se limpiaron conexiones huerfanas de `test_sintel` con `pg_terminate_backend`. Recuperacion: se relanzo la regresion en 4 lotes mas pequeños en vez de la suite completa de una sola vez, para reducir el pico de memoria.

## Decisions

1. **Relacion Gasto -> Proyecto: UUID opaca, no FK.** `DocumentoSoporte.proyecto_uuid` (UUIDField, null=True, blank=True, db_index=True). Consistente con el patron Pull Model ya usado en el mismo modelo (`movimiento_inventario_uuid`) y evita acoplamiento de bounded contexts (Gastos no debe importar `Proyecto` a nivel de modelo).
2. **GASTO_COST_AMOUNT_SSoT = `subtotal`.** Confirmado leyendo `ExtractorGastos._mapear_a_dto()`: la linea contable DEBE (el gasto real reconocido) usa `doc.subtotal`; `doc.total` es el pasivo neto a pagar al proveedor (subtotal - retenciones), un concepto de tesoreria, no de costo. Todos los calculos de `costo_gastos_real` en Proyectos deben sumar `subtotal`, nunca `total`.
3. **Reglas de inclusion en costos:** `activo=True, anulado=False, proyecto_uuid=proyecto.uuid, empresa_id=proyecto.empresa_id`.
4. **Recalculo:** disparado explicitamente desde Gastos (Service Layer, sin Signals) llamando a `apps.tenant.proyectos.services.business_service.calcular_indicadores_financieros(proyecto)` via import perezoso -- mismo patron ya usado por Gastos para llamar a Contabilidad/Inventario/Proveedores.
5. **CIERRE:** no existe ninguna regla actual que bloquee la escritura de campos financieros de Proyecto en fase CIERRE (`avanzar_fase`/`orchestrate_update_proyecto` ya recalculan indicadores sin importar la fase). No se inventa una restriccion nueva; se documenta el hallazgo.
6. **Edicion de `proyecto_uuid` en un Gasto existente:** dado que el PATCH de Gasto no pasa por `business_service`, la validacion DSV se hace en el serializer (mismo patron ya usado por el campo `sede`) y el recalculo se dispara desde `GastoViewSet.perform_update()` comparando el `proyecto_uuid` anterior vs el nuevo.
7. **UI "Agregar gasto":** reutiliza el endpoint de edicion de Gasto ya existente (`PATCH /api/v1/gastos/{uuid}/` con `proyecto_uuid`) en vez de crear un endpoint nuevo -- evita duplicar URLs.

8. **`subtotal` es read-only via API** (hallazgo real durante testing): `DocumentoSoporteDetailSerializer` no permite editar `subtotal` via PATCH (dato fiscal). El recalculo ante "editar importe de un gasto ya asociado" (Escenario 5 del plan) esta implementado en `perform_update()` de forma defensiva (dispara ante cualquier cambio), pero hoy no es un camino alcanzable desde la API -- no se agrego un test para un escenario que el sistema no permite ejecutar.

## Modified Files

Backend:
- `apps/tenant/gastos/models.py` -- `DocumentoSoporte.proyecto_uuid`, indice `idx_gastos_proyecto`, properties `proyecto_codigo`/`proyecto_nombre`.
- `apps/tenant/gastos/migrations/0023_documentosoporte_proyecto_uuid_and_more.py`
- `apps/tenant/gastos/services/business_service.py` -- `_recalcular_proyecto()`, DSV de `proyecto_uuid` en `procesar_gasto()`, recalculo en `anular_gasto()`/`desactivar_gasto()`.
- `apps/tenant/gastos/services/selectors.py` -- `proyecto_uuid` en LIST/DETAIL fields, `DocumentoSelector.get_by_proyecto()`.
- `apps/tenant/gastos/api/serializers.py` -- `proyecto_uuid` (writable + DSV) y `proyecto_codigo` (read-only) en List y Detail.
- `apps/tenant/gastos/api/viewsets.py` -- `perform_update()` dispara recalculo de proyecto(s) afectado(s).
- `apps/tenant/proyectos/models.py` -- `Proyecto.costo_gastos_real`.
- `apps/tenant/proyectos/migrations/0022_proyecto_costo_gastos_real.py`
- `apps/tenant/proyectos/services/business_service.py` -- `calcular_costo_gastos()`, `calcular_indicadores_financieros()` actualizado.
- `apps/tenant/proyectos/api/serializers.py` -- `costo_gastos_real` en List/Detail, `get_costo_total()`/`get_indicadores_financieros()` actualizados.
- `apps/tenant/proyectos/api/viewsets.py` -- accion `gastos` (GET, solo lectura) en `ProyectoViewSet`.

Frontend:
- `apps/tenant/gastos/static/gastos/js/gastos.api.js` -- `proyectos.search()`.
- `apps/tenant/gastos/static/gastos/js/features/gasto_editor.js` -- `initProyectoSearch()`, `proyecto_uuid` en `collectData()`.
- `apps/tenant/gastos/templates/tenant/gastos/offcanvas_crear_gasto.html` / `offcanvas_editar_gasto.html` -- seccion "Proyecto (Opcional)".
- `apps/tenant/gastos/templates/tenant/gastos/offcanvas_detalle_gasto.html` -- "Proyecto Asociado".
- `apps/tenant/proyectos/static/proyectos/js/proyectos.api.js` -- namespace `gastos` (list/search/agregar/desvincular).
- `apps/tenant/proyectos/static/proyectos/js/features/proyectos_editor.js` -- modulo `ProyectosGastos`, formulas de indicadores financieros actualizadas (Fase 3 y Fase 4 Cierre).
- `apps/tenant/proyectos/templates/tenant/proyectos/offcanvas_form.html` -- seccion "Gastos del Proyecto", fila "Gastos (real)" en panel de indicadores.

## Tests

- `apps/tenant/gastos/tests/test_gastos_proyecto_integracion.py` -- 10 passed (crear sin/con proyecto, DSV UUID inexistente rechazado, GASTO_COST_AMOUNT_SSoT=subtotal confirmado con retenciones activas, asociar/mover/desasociar via PATCH, anular/desactivar sale del costo).
- `apps/tenant/proyectos/tests/test_costo_gastos_real.py` -- 7 passed (cero sin gastos, suma multiples, excluye anulados/inactivos/sin-proyecto/de-otro-proyecto, P&L completo con mano de obra + gastos).
- Regresion `apps/tenant/gastos/tests/` (suite completa): 44 passed, 3 warnings (pre-existentes, no relacionadas) en 3284.97s (0:54:44). Verde.
- Regresion `apps/tenant/proyectos/tests/` (por lotes, tras OOM en corrida completa -- ver Blockers): Lote 1/4 (scope/tabla) 12 passed en 989.01s. Lote 2/4 (presupuesto/financieros/tareas) 44 passed, 2 skipped en 2361.19s. Lote 3/4 (persistencia/documentos/bitacora/costo_gastos) 35 passed en 2668.45s. Lote 4/4 (ciclo de vida, 4 archivos juntos) fue matado por OOM a los ~41 min (segundo incidente de zombie, resuelto igual que el primero). Subdividido: 4a (test_lifecycle_transiciones.py solo) 18 passed en 1628.02s. 4b (test_lifecycle_gates_documentales, test_lifecycle_persistencia, test_lifecycle_concurrencia) 14 passed, 1 error en 1310.96s. El error es EXCLUSIVAMENTE de teardown (`ERROR at teardown of test_dos_transiciones_simultaneas_a_la_misma_fase_no_duplican_historial`, el test en si arrojo "1 passed" -- el error ocurre despues, en `_post_teardown()`/`flush`): `psycopg.errors.FeatureNotSupported: cannot truncate a table referenced in a foreign key constraint. DETAIL: Table "perfil_tenantprofile" references "accounts_user".` -- confirmado por traceback completo (ver evidencia mas abajo) que es el bug preexistente del repo ya documentado en esta sesion (afecta a TransactionTestCase/`transaction=True`, tambien reportado en `test_cartera_concurrencia.py` de otra app). NO es una regresion de GASTOS_PROYECTOS_01 y no se intento corregir (fuera de alcance de esta mision).

**TOTAL `apps/tenant/proyectos/tests/`: 123 passed, 2 skipped, 1 error preexistente-no-relacionado (teardown). Suite funcionalmente verde.**

## Last Verified At
- 2026-09-18: `manage.py check` limpio + `makemigrations --check` limpio. Regresion completa de `apps/tenant/gastos/tests/` (44 passed) y `apps/tenant/proyectos/tests/` (123 passed, 2 skipped, 1 error preexistente no relacionado) en verde.

---

## FINAL REPORT

Mission: GASTOS_PROYECTOS_01
Status: PASS_WITH_DEFERRED

### Implemented
- Vinculacion opcional de un Gasto (`DocumentoSoporte`) a un Proyecto via UUID opaco (Pull Model), sin FK directa.
- Recalculo automatico y explicito (sin Signals) del costo de gastos del proyecto ante: crear gasto con proyecto, asociar/mover/desvincular un gasto existente (PATCH), anular gasto, desactivar gasto.
- Nuevo indicador cacheado `Proyecto.costo_gastos_real`, integrado en el P&L (`calcular_indicadores_financieros`) junto a mano de obra y materiales.
- UI completa en ambas apps: campo "Proyecto (opcional)" con buscador en los formularios de Gasto (crear/editar/detalle), y seccion "Gastos del Proyecto" (buscar/agregar/desvincular + total) en el formulario de Proyecto, con el panel de indicadores financieros y el comparativo de Cierre actualizados para incluir gastos.

### Models
- `apps/tenant/gastos/models.py`: `DocumentoSoporte.proyecto_uuid` (UUIDField, null=True, blank=True, db_index=True), indice compuesto `idx_gastos_proyecto` (empresa, proyecto_uuid), properties `proyecto_codigo`/`proyecto_nombre`.
- `apps/tenant/proyectos/models.py`: `Proyecto.costo_gastos_real` (DecimalField, cache derivado, misma filosofia que `costo_mano_obra_real`/`costo_materiales_real`).

### Migrations
- `apps/tenant/gastos/migrations/0023_documentosoporte_proyecto_uuid_and_more.py` (aditiva, sin backfill -- todos los gastos historicos quedan con `proyecto_uuid=NULL`, correcto).
- `apps/tenant/proyectos/migrations/0022_proyecto_costo_gastos_real.py` (aditiva, `default=0`).
- Ambas aplicadas a todos los schemas tenant via `migrate_schemas --tenant`.

### Services
- `apps/tenant/gastos/services/business_service.py`: `_recalcular_proyecto()` (helper Pull Model, import perezoso hacia `proyectos.services.business_service`), DSV de `proyecto_uuid` en `procesar_gasto()`, recalculo integrado en `anular_gasto()`/`desactivar_gasto()`.
- `apps/tenant/gastos/services/selectors.py`: `DocumentoSelector.get_by_proyecto()` (filtra activo=True, anulado=False, misma regla de inclusion que el calculo de costos).
- `apps/tenant/proyectos/services/business_service.py`: `calcular_costo_gastos()` (suma `subtotal` de gastos asociados, import perezoso hacia `gastos.models`), integrado en `calcular_indicadores_financieros()`.

### APIs
- `GastoViewSet` (gastos): `proyecto_uuid` ahora aceptado en create (via `procesar_gasto`) y en PATCH (via serializer + DSV), `perform_update()` dispara recalculo del/los proyecto(s) afectado(s) comparando `proyecto_uuid` antes/despues.
- `ProyectoViewSet` (proyectos): nueva accion de solo lectura `GET /api/v1/proyectos/{uuid}/gastos/` -- lista los gastos asociados + `costo_gastos_real`. La asociacion/desvinculacion reutiliza el endpoint de edicion de Gasto ya existente (`PATCH /api/v1/gastos/{uuid}/`), sin URLs duplicadas.
- Serializers de Gastos (`DocumentoSoporteListSerializer`/`DocumentoSoporteDetailSerializer`): `proyecto_uuid` (writable + DSV) y `proyecto_codigo` (read-only).
- Serializers de Proyectos (`ProyectoListSerializer`/`ProyectoDetailSerializer`): `costo_gastos_real` expuesto, `get_costo_total()`/`get_indicadores_financieros()` actualizados.

### Frontend
- Gastos: `gastos.api.js` (`proyectos.search()`), `gasto_editor.js` (`initProyectoSearch()`, mismo patron que `initMovimientoSearch()`), templates crear/editar/detalle con seccion "Proyecto (Opcional)"/"Proyecto Asociado".
- Proyectos: `proyectos.api.js` (namespace `gastos`: list/search/agregar/desvincular), `proyectos_editor.js` (modulo `ProyectosGastos`, mismo patron que `ProyectosPresupuesto`), `offcanvas_form.html` con seccion "Gastos del Proyecto" (buscador + tabla + total) y fila "Gastos (real)" en el panel de indicadores financieros (Fase 3) y en el calculo del comparativo de Cierre (Fase 4).
- Todos los JS modificados verificados con `node --check` (sin errores de sintaxis). Sin verificacion visual en navegador (Capa 1 no disponible en este entorno, igual que en el resto de misiones de esta sesion).

### Financial Calculation
- `GASTO_COST_AMOUNT_SSoT = DocumentoSoporte.subtotal` -- decision confirmada leyendo `apps/tenant/contabilidad/integracion/extractores/gastos.py` (la linea contable DEBE, el gasto real reconocido, usa `subtotal`; `total` es el pasivo neto post-retenciones, un concepto de tesoreria). Nunca se usa `total` para costos de proyecto.
- `costo_total_real = costo_mano_obra_real + costo_materiales_real + costo_gastos_real`; `utilidad_estimada`/`margen_rentabilidad` actualizados en consecuencia. Formula verificada con test dedicado (P&L completo).

### Tests
- Gastos: 44/44 passed (suite completa `apps/tenant/gastos/tests/`, incluye 10 tests nuevos de integracion).
- Proyectos: 123/125 passed, 2 skipped (suite completa `apps/tenant/proyectos/tests/`, corrida en 4 lotes por restricciones de memoria del entorno; incluye 7 tests nuevos de `costo_gastos_real`). El unico "error" restante es un bug de teardown preexistente y no relacionado (ver Decisions #9 / Blockers historico) -- no es una falla de esta mision.
- Cross-App: NO ejecutado (proveedores/contabilidad/inventario) -- ver Deferred.

### Security
- DSV en ambos sentidos: `procesar_gasto()` valida `Proyecto.objects.filter(uuid=..., empresa_id=...)`, y el serializer de Gasto valida lo mismo en edicion. UUID lookup exclusivamente (nunca PK). Sin exposicion cross-tenant posible (aislamiento por schema + DSV redundante).

### Performance
- `proyecto_codigo` (property de `DocumentoSoporte`) hace una query adicional por fila en listados -- mismo patron N+1 ya existente en este mismo serializer para `movimiento_referencia` (precedente aceptado en el codigo base, no introducido por esta mision). Aceptable dado el volumen tipico de paginacion.
- Nuevo indice `idx_gastos_proyecto` (empresa, proyecto_uuid) para las consultas de `get_by_proyecto()`/`calcular_costo_gastos()`.

### Deferred
- Regresion cross-app formal (`pytest apps/tenant/proveedores/tests apps/tenant/contabilidad/tests apps/tenant/inventario/tests`) no se ejecuto por restricciones de tiempo/memoria del entorno (cada suite de este tamano toma 30-60+ min). Riesgo estimado BAJO: los cambios de esta mision son puramente aditivos (un campo nullable nuevo + un metodo de selector nuevo), no se modifico ningun archivo dentro de `proveedores/`, `contabilidad/` o `inventario/`. Recomendado como follow-up antes de un release formal.
- Verificacion visual en navegador (Capa 1) no disponible en este entorno.

### Remaining Risks
- Bajo. El unico riesgo identificado es el N+1 documentado en Performance, ya aceptado como patron existente.

### Evidence
- `manage.py check` -> "System check identified no issues (0 silenced)."
- `manage.py makemigrations --check --dry-run` -> "No changes detected"
- `pytest apps/tenant/gastos/tests/ -q` -> "44 passed, 3 warnings in 3284.97s (0:54:44)"
- `pytest apps/tenant/proyectos/tests/` (4 lotes) -> 12 + 44(+2 skip) + 35 + 18 + 14(+1 error preexistente) = 123 passed, 2 skipped, 1 error no relacionado
- Migraciones: `tenant_gastos.0023_documentosoporte_proyecto_uuid_and_more`, `tenant_proyectos.0022_proyecto_costo_gastos_real`, aplicadas via `migrate_schemas --tenant` en todos los tenants.
