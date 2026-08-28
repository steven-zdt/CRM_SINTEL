# REM-P3-11 — Código muerto en Proveedores (retenciones hardcodeadas)

**Estado:** VERIFIED (ya estaba resuelto — no requirió acción)
**Prioridad:** P3
**App involucrada:** `proveedores`
**Fecha:** 2026-08-28

## Hallazgo original

`ProveedorBusinessService.obtener_configuracion_retenciones()`/
`calcular_componentes_retencion()`/`calcular_neto_gasto()` — funciones con
tarifas hardcodeadas (Retefuente 4%, ReteICA 0.966%) documentadas como
código muerto confirmado en `documentacion/audits/apps/
APP_proveedores_NORMATIVE_MATRIX.md` (2026-08-21).

## Verificación

Grep de los 3 nombres de función en todo `apps/tenant/proveedores/`
(excluyendo `.agent/`, que son documentos históricos, no código) →
**cero resultados**. Las funciones ya no existen en
`apps/tenant/proveedores/services/business_service.py`.

## Conclusión

**Ya fueron eliminadas en una limpieza previa a esta sesión** (consistente
con `documentacion/audits/apps/F34_MASTER_FINAL.md`, que documenta
limpiezas de código muerto en `proveedores` durante la misión F34,
2026-08-21 — "~76 líneas + imports"). No requirió ninguna acción en esta
remediación — se verifica y se cierra el ítem con evidencia negativa, sin
tocar código.

## Governance

N/A — sin cambio de código (nada que corregir).
