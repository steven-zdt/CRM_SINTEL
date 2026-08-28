# REM-P3-01 — Dashboard sin extractor de Compras

**Estado:** DEFERRED (requiere trabajo nuevo, no una corrección)
**Prioridad:** P3
**Apps involucradas:** `compras`, `dashboard`
**Fecha:** 2026-08-28

## Hallazgo

El Dashboard no consolida órdenes de compra pendientes de recepción — no
existe `apps/tenant/dashboard/services/extractores/compras_ext.py`.

## Investigación (regla explícita del plan: verificar el patrón Reporting Hub antes de agregar el extractor)

El plan pide preferir `Compras Provider → Reporting Hub → Dashboard` en
vez de construir el extractor directo. Se verificó: **`apps/tenant/
compras/reporting/` no existe** — `compras` no tiene ningún provider de
Reporting Hub hoy (a diferencia de `inventario`, `gastos`, `ventas`,
`facturas`, `contabilidad`, que sí lo tienen).

## Decisión

**No se implementa en esta sesión.** Cerrar este hallazgo correctamente
requiere construir DESDE CERO: (1) `compras/reporting/provider.py` (nuevo
archivo, nueva responsabilidad), (2) `dashboard/services/extractores/
compras_ext.py` (nuevo extractor), (3) su DTO, (4) su entrada en el
serializer del dashboard, (5) su tarjeta en el frontend. Esto es
funcionalidad nueva construida sobre un patrón existente, no una
corrección de un defecto — la Regla de No Expansión del plan
("no crear... salvo que el hallazgo no pueda corregirse limpiamente con
la arquitectura actual") aplica aquí en sentido inverso: la arquitectura
SÍ soporta esto limpiamente (el patrón Reporting Hub ya existe y es
replicable), pero construirlo es una pieza de trabajo genuina, no un fix
de 15 minutos.

## Alcance para una sesión dedicada futura

1. `apps/tenant/compras/reporting/provider.py` — exponer al menos
   "órdenes pendientes de recepción" (`OrdenCompra.estado in
   ['APROBADA','PARCIAL']`) y "próximas a vencer" si hay fecha de
   entrega esperada.
2. `apps/tenant/dashboard/services/extractores/compras_ext.py` — mismo
   patrón Pull que los 7 extractores existentes.
3. `WidgetComprasDTO` + entrada en `DashboardMetricasDTO`/serializer.
4. Tarjeta nueva en `dashboard_main.js`.

## Governance

N/A — sin cambio de código en esta sesión.
