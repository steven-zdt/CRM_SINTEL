# Reporting Hub — Baseline (FASE 0)

**Fecha:** 2026-08-26
**Alcance:** Investigacion previa a construir `apps/services/reporting/`. No se modifico codigo durante esta fase.

---

## 1. Que existe hoy relacionado con reporting

**No existe ningun servicio transversal de reporting.** `documentacion/arquitectura_general.md` (v3.59.0) no tiene ninguna seccion dedicada a reporting/analytics/KPI backend — solo referencias sueltas:

- **Dashboard** (`apps/tenant/dashboard/`, modelo `SnapshotMetricaDiaria`) — el unico agregador cross-app real que existe hoy. Patron: un extractor por dominio (`services/extractores/{facturas,inventario,empleados,gastos,proveedores,proyectos,clientes,sedes}_ext.py`), cada uno con un metodo estatico `extraer_metricas(empresa_id)` que lee via el `Selectors` del dominio (nunca `models.py` directo) y devuelve un DTO congelado (`services/dtos.py`). `DashboardBusinessService.obtener_metricas_consolidadas()` orquesta los 8 extractores, cachea en Redis 15 min. Un Celery Beat nocturno (`tasks.py`) materializa `SnapshotMetricaDiaria`.
  - **Por que NO es lo mismo que Reporting Hub** (verificado, no asumido): cada extractor devuelve una forma FIJA (5-6 numeros por widget), sin dimensiones/filtros/paginacion declarables por el usuario. Es "calcular estos KPIs fijos", no "consultar un dataset con filtros arbitrarios declarados". No hay registry/plugin — cada extractor esta importado a mano en el business service.
  - **Conclusion:** no se duplica nada al construir Reporting Hub; el patron de "extractor por dominio, nunca toca `models.py` directo" SI se reutiliza como inspiracion de diseño (mismo principio Pull Model que ya usa Contabilidad).
- **Contabilidad** (`apps/tenant/contabilidad/`) — ya tiene 3 reportes reales y correctos: `balance_prueba_selector`, `estado_resultados_selector`, `get_libro_diario_periodo` (`services/selectors.py:578,681,762`). Por regla explicita de esta mision, Reporting NO absorbe esta logica — solo la envuelve en un adapter de solo lectura.
- **Exportacion (CSV/XLSX/PDF): no existe ningun exportador en todo el repo.** Confirmado por grep exhaustivo — todo hit de `openpyxl`/`csv` es del lado de IMPORTACION (parseo de Excel subido), no exportacion. Se construye desde cero.
- **Celery + reportes:** solo las 3 tareas de `dashboard/tasks.py`. Ninguna otra app tiene una tarea Celery de reporte/export.
- **`docs/reporting/`:** no existia antes de esta mision.

## 2. Infraestructura reutilizable confirmada (Regla Absoluta #6 — no crear RBAC nuevo)

El **Scope Engine** que la mision pide en FASE 10/11 **ya existe, completo y probado**, en `apps/tenant/core/services/`:

- `organizational_context.py::OrganizationalContext` — "donde estoy parado ahora" (una sede activa). `.resolve(request)`, `.filter(model)`.
- `organizational_scope.py::OrganizationalScope` — "que subconjunto TOTAL puedo tocar" (conjunto completo de sedes/areas asignadas, no una sola activa). `.resolve(request)`, `.permits_sede(id)`, `.permits_area(id)`, `.filter(model)`.
- `organizational_filters.py::filter_by_scope()` / `filter_by_scope_null_safe()` — helpers de filtrado por conjunto.

**Decision de diseño:** el Scope Engine de Reporting Hub es un envoltorio delgado sobre `OrganizationalScope` (no una reimplementacion). `permits_sede()`/`permits_area()` son exactamente la funcion de "interseccion" que la mision pide en FASE 11 (filtro solicitado vs. alcance del usuario).

## 3. Precedente de forma para el nuevo servicio

`apps/services/document_intake/` (`contracts.py` + `dispatcher.py`, mision Mail Hub anterior) es la plantilla directa: dataclasses congeladas + `Protocol` `runtime_checkable` + un registry singleton a nivel de modulo (`register()`/`get()`), poblado lazily por cada dominio via su propio `AppConfig.ready()`. Reporting Hub sigue esta misma forma para `ReportProvider`/`ReportRegistry`.

## 4. Datasets/selectors agregados ya reusables (evitan reescribir consultas)

| App | Metodo | Ubicacion |
|---|---|---|
| Facturas | `FacturaSelectors.get_summary(empresa_id)` | `apps/tenant/facturas/services/selectors.py:186` |
| Gastos | `DocumentoSoporteSelectors.get_summary(empresa_id)` | `apps/tenant/gastos/services/selectors.py:215` |
| Ventas | ninguno — solo `get_list`/`get_detail` | `apps/tenant/ventas/services/selectors.py:119,147` |
| Inventario | sin "resumen"; existen `calcular_stock_sede`, `get_movimientos_timeline` | `apps/tenant/inventario/services/selectors.py:360,528` |
| Contabilidad | `balance_prueba_selector`, `estado_resultados_selector`, `get_libro_diario_periodo` (NO migrar, solo envolver) | `apps/tenant/contabilidad/services/selectors.py:578,681,762` |

## 5. Dependencias disponibles para exportacion

`requirements.txt` ya incluye `openpyxl` (usado hoy solo para lectura). **No hay libreria de PDF instalada** (`reportlab`/`weasyprint` ausentes). Decision: construir JSON + CSV (stdlib) + XLSX (openpyxl) en esta pasada; PDF queda explicitamente diferido — agregar una libreria de PDF es una decision de dependencia que corresponde confirmar, no asumir.

## 6. Riesgos identificados antes de construir

- Construir un "mega-servicio" que importe modelos de cada app directamente (Regla Absoluta #1) — mitigado por diseño: `apps/services/reporting/` solo define contratos + registry + query engine + exporters; toda consulta real vive en `apps/tenant/<app>/reporting/provider.py`.
- Duplicar el Scope Engine (Regla Absoluta #6) — mitigado, ver §2.
- Sobre-construir antes de tener evidencia (Regla Absoluta #7) — mitigado: un solo dataset real end-to-end (Ventas) + un adapter de Contabilidad se implementan esta pasada; el resto queda como loop de expansion documentado (FASE 40), no como trabajo a medias.
