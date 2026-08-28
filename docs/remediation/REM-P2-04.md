# REM-P2-04 — Retenciones sufridas (cliente retiene sobre lo que nos paga)

**Estado:** VERIFIED (confirmado que SÍ existe — no era un gap real, era
una verificación pendiente de la auditoría empresarial previa)
**Prioridad:** P2
**App involucrada:** `facturas`, `contabilidad`
**Fecha:** 2026-08-28

## Contexto

La auditoría empresarial de esta sesión (`BUSINESS_GAP_MATRIX.md`) dejó
esto marcado explícitamente como **no confirmado, requiere verificación
dirigida**: ¿existe en SINTEL el caso en que un cliente actúa como agente
retenedor y practica retención sobre lo que nos paga (dirección inversa a
la ya confirmada Retefuente/ReteICA/ReteIVA que la empresa practica a sus
proveedores)?

## Investigación

Grep dirigido de `RetencionesService.obtener_retenciones_desde_tercero(...,
naturaleza='VENTA', ...)` encontró:

- `FacturaBusinessService.obtener_retenciones_desde_cliente()`
  (`apps/tenant/facturas/services/business_service.py:295-340`) — llama a
  `RetencionesService.obtener_retenciones_desde_tercero(tipo_tercero=
  'CLIENTE', naturaleza='VENTA', ...)`, exactamente el mecanismo Pull
  Model ya confirmado como correcto para Retefuente/ReteICA/ReteIVA del
  lado de compras, aplicado aquí en la dirección inversa (config del
  Cliente, no del Proveedor).
- **Consumidor real confirmado**: `apps/tenant/facturas/services/
  api_mixins.py:55` expone este método vía el endpoint real `/api/v1/
  facturas/obtener-retenciones/` (documentado en `.agent/
  COMPLETO_FLUJO_FACTURAS.md:413`, disponible desde v3.12.0) — no es
  código muerto, tiene un consumidor HTTP real.
- **Persistencia real confirmada**: `guardar_desde_dto()`
  (`business_service.py:775-788`) llama `RetencionesService.
  crear_retencion()` para cualquier `Factura` (VENTA o COMPRA) cuyo DTO
  traiga montos de `retefuente`/`reteica`/`reteiva` — los registra en
  `contabilidad.Retencion`, el mismo ledger real ya verificado en
  `TAX_COMPLIANCE_MATRIX.md`.

## Conclusión

**No es un gap.** El mecanismo de retención sufrida (cliente actuando
como agente retenedor sobre una venta nuestra) existe, está conectado a un
endpoint real, y persiste en el mismo `Retencion` ledger central — mismo
nivel de madurez arquitectónica que el flujo ya confirmado en `gastos`
(dirección compra). Se corrige la clasificación de
`documentacion/auditoria_empresarial/BUSINESS_GAP_MATRIX.md` (que lo
dejaba como "GAP no confirmado") a **CONFIRMADO_EXISTE**.

## Nota de calidad encontrada durante la verificación (no corregida — fuera de alcance de P2-04)

`RetencionesService.crear_retencion()` (llamado en `business_service.py:781`)
no recibe el parámetro `naturaleza` explícito — usa el default
`naturaleza='VENTA'` del propio `crear_retencion()`
(`retenciones_service.py:154`) **incondicionalmente, incluso para
Facturas de COMPRA** procesadas por el mismo `guardar_desde_dto()`. Esto
podría etiquetar como `VENTA` una retención que en realidad corresponde a
una `COMPRA` (el proveedor nos retuvo, no al revés) cuando se importa un
XML de factura de compra con líneas de retención propias. **No se
corrigió en esta sesión** — requiere confirmar primero, con datos reales,
si esto afecta algún reporte que agregue por `naturaleza` (ej.
`tax.retenciones` del Reporting Hub) antes de tocarlo; se documenta aquí
como hallazgo nuevo para una futura corrección dirigida, no se improvisa
un fix sin esa verificación.

## Governance

N/A — sin cambio de código en este ítem (solo investigación y
reclasificación documental).
