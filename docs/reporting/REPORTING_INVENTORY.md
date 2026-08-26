# Reporting Hub — Inventario Global de Reportes (FASE 1)

**Fecha:** 2026-08-26
**Metodo:** auditoria de codigo real (grep exhaustivo + lectura directa), no inferencia de intencion.

---

## Clasificacion por app tenant

| App | Reporte/KPI real encontrado | Clasificacion | Datos usados | Filtros/Dimensiones | Exportacion | Consumidor | Estado |
|---|---|---|---|---|---|---|---|
| Dashboard | `obtener_metricas_consolidadas()` (8 widgets fijos: facturas, inventario, empleados, gastos, proveedores, proyectos, clientes, sedes) | **TRANSVERSAL** | Lee via Selectors de 8 apps distintas | Ninguno declarable (fijo por diseño) | No | UI Dashboard ejecutivo | OPERATIVO (funcional, cacheado, snapshot nocturno) |
| Contabilidad | Balance de Prueba, Estado de Resultados, Libro Diario | **FINANCIERO** | `MovimientoContable`/`AsientoContable` propios | fecha_inicio, fecha_fin, empresa | No (solo JSON via API) | UI Contabilidad (`reporte_page.html`) | OPERATIVO (validado en vivo, mision CONT-19) |
| Facturas | `FacturaSelectors.get_summary(empresa_id)` | DOMINIO (agregado simple) | `Factura`/`NotaCredito` | ninguno declarable, empresa fija | No | Dashboard (`facturas_ext.py`) | OPERATIVO como fuente interna, no expuesto como reporte propio |
| Gastos | `DocumentoSoporteSelectors.get_summary(empresa_id)` | DOMINIO (agregado simple) | `DocumentoSoporte` | mes actual fijo | No | Dashboard (`gastos_ext.py`) | OPERATIVO como fuente interna, no expuesto como reporte propio |
| Clientes | `CarteraViewSet.kpis()` | DOMINIO | `Cartera` | — | No | UI Clientes | OPERATIVO, propio del dominio |
| Ventas | ninguno | — | — | — | — | — | **NO_IMPLEMENTADO** (solo `get_list`/`get_detail`, sin agregado) |
| Inventario | ninguno dedicado; existen agregados parciales (`calcular_stock_sede`, `get_movimientos_timeline`) | DOMINIO (parcial) | `MovimientoInventario`/`Producto` | sede | No | Dashboard (`inventario_ext.py`) | PARCIAL |
| Empleados | via extractor Dashboard unicamente | DOMINIO | `Devengo`/`Empleado` | — | No | Dashboard | PARCIAL (solo como fuente de Dashboard) |
| Proveedores | via extractor Dashboard unicamente | DOMINIO | `Proveedor`/`CuentasPagar` | — | No | Dashboard | PARCIAL |
| Proyectos | via extractor Dashboard unicamente | DOMINIO | `Proyecto` | — | No | Dashboard | PARCIAL |
| Compras | ninguno | — | — | — | — | — | NO_IMPLEMENTADO |
| Cotizaciones | ninguno | — | — | — | — | — | NO_IMPLEMENTADO |
| Proveedores (cartera) | ver arriba | — | — | — | — | — | — |
| Bancos | ninguno (solo conciliacion manual) | — | — | — | — | — | NO_IMPLEMENTADO |
| Empresa/Perfil/Core | sin reportes propios (infraestructura) | — | — | — | — | — | NO_APLICA |

## Exportadores existentes en todo el repo

**Ninguno.** Confirmado por grep exhaustivo de `openpyxl|reportlab|xlsxwriter|import csv` — todos los hits son de importacion (parseo), cero de exportacion. No hay `HttpResponse` con `content_type` CSV/XLSX/PDF en ningun lado del codigo actual.

## Duplicaciones detectadas (FASE 2, adelantada aqui por ser trivial de resolver)

- **Ninguna duplicacion de logica real encontrada.** Facturas y Gastos calculan SUS PROPIOS totales una sola vez (`get_summary`), y Dashboard los CONSUME via el extractor — no hay una segunda formula paralela para el mismo numero. Clasificacion: **KEEP** (SAME_DATA_DIFFERENT_PURPOSE en el peor caso: Dashboard usa el resumen para un widget ejecutivo; Reporting Hub lo reutilizaria igual para un dataset filtrable — mismo dato, propositos complementarios, no conflictivos).
- Contabilidad es la unica app con reportes financieros reales y NO se toca (regla explicita de la mision).

## Matriz SSoT (FASE 3, adelantada — trivial dado el inventario)

| Dataset (a construir) | SSoT | Provider (a construir) | Consumidores previstos |
|---|---|---|---|
| `ventas.resumen` | `apps/tenant/ventas` | `apps/tenant/ventas/reporting/provider.py` | Reporting Hub (nuevo), futuro Dashboard |
| `contabilidad.balance_prueba` | `apps/tenant/contabilidad` (calculo permanece alli) | `apps/tenant/contabilidad/reporting/provider.py` (adapter de solo lectura) | Reporting Hub (nuevo) |
| `contabilidad.estado_resultados` | `apps/tenant/contabilidad` (calculo permanece alli) | mismo adapter | Reporting Hub (nuevo) |

Datasets de Inventario/Facturas/Gastos/Empleados quedan **fuera de esta pasada** (ver `REPORTING_ARCHITECTURE.md` §"Loop de expansion, FASE 40") — el patron queda probado y documentado con Ventas + Contabilidad, replicable mecanicamente sin volver a auditar arquitectura.
