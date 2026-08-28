# REM-P3-02 — Dashboard sin extractor de Bancos

**Estado:** DEFERRED (requiere trabajo nuevo, no una corrección)
**Prioridad:** P3
**Apps involucradas:** `bancos`, `dashboard`
**Fecha:** 2026-08-28

## Hallazgo

El Dashboard no consolida transacciones bancarias sin conciliar — no
existe `apps/tenant/dashboard/services/extractores/bancos_ext.py`.

## Investigación

Igual que `REM-P3-01`: `apps/tenant/bancos/reporting/` **no existe** —
`bancos` no tiene provider de Reporting Hub. Mismo diagnóstico.

## Decisión

**No se implementa en esta sesión** — mismo razonamiento que `REM-P3-01`:
es funcionalidad nueva sobre un patrón existente, no una corrección.

## Alcance para una sesión dedicada futura

1. `apps/tenant/bancos/reporting/provider.py` — al menos "transacciones
   sin conciliar" (`TransaccionBancaria.conciliado=False`) por cuenta.
2. `apps/tenant/dashboard/services/extractores/bancos_ext.py`.
3. `WidgetBancosDTO` + entrada en `DashboardMetricasDTO`/serializer.
4. Tarjeta nueva en `dashboard_main.js`.

## Governance

N/A — sin cambio de código en esta sesión.
