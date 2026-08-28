# REM-P3-10 — Venta ↔ Factura: la relación real ya existe (corrección de la auditoría)

**Estado:** VERIFIED (hallazgo original de la auditoría era impreciso —
la relación real SÍ existe, corregido el registro)
**Prioridad:** P3
**App involucrada:** `ventas`, `facturas`
**Fecha:** 2026-08-28

## Hallazgo original (impreciso)

`BUSINESS_GAP_MATRIX.md` (auditoría empresarial) reportaba: *"Factura no
tiene ningún campo persistido hacia Venta (`venta_uuid`) pese a que un
comentario del propio código sugiere que debería tenerlo — el vínculo real
es solo por igualdad de string (`numero_factura`==`numero`)."*

## Investigación

`Venta.factura_asociada` (`apps/tenant/ventas/models.py:174-181`) es un
**`OneToOneField` real** hacia `facturas.Factura`
(`on_delete=SET_NULL, related_name='venta_origen'`). Esto significa:

- `venta.factura_asociada` → la Factura vinculada (desde el lado Venta).
- `factura.venta_origen` → la Venta origen (desde el lado Factura, vía el
  `related_name` de Django — no requiere un campo físico duplicado en la
  tabla de Factura).

La relación real **sí existe y es una FK de BD real, no una coincidencia
de string** — mi lectura original del código (que solo miró
`numero_factura` como texto) fue incompleta.

## Decisión

**No se crea ninguna relación nueva.** Crear un segundo campo redundante
(`Factura.venta_uuid`) duplicaría exactamente lo que `related_name=
'venta_origen'` ya resuelve — violaría la regla explícita del plan de
remediación: *"NO crear segunda relación redundante si la existente
resuelve correctamente el negocio."* Se corrige únicamente el registro de
la auditoría (`BUSINESS_GAP_MATRIX.md` §LOW, fila "Factura sin campo
persistido hacia Venta") para reflejar la realidad verificada.

## Archivos modificados

Ninguno (código). Se corrige la clasificación en
`documentacion/auditoria_empresarial/BUSINESS_GAP_MATRIX.md`.

## Governance

N/A — sin cambio de código.
