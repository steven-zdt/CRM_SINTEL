# F34_ventas_AUDIT — Auditoria integral de negocio/arquitectura (app 8/16)

Mision F34. Base confirmada: `documentacion/audits/apps/
APP_ventas_AUDIT.md` (0 codigo muerto; hallazgo P1 heredado --
transmision DIAN nunca implementada, verificado y resuelto con
evidencia completa en `facturas`).

**Fecha:** 2026-08-21. **Rama:** `feat/onboarding-cookie`.
**Nota:** sin ejecucion de tests (instruccion explicita del usuario)
-- validacion por evidencia estatica.

---

## Resumen ejecutivo

`ventas` orquesta el registro comercial y el pre-proceso de
facturacion DIAN (DTO UBL 2.1, resolucion, consecutivo). Sin cambios
de codigo en esta pasada -- barrido fresco (752 lineas, 15 metodos,
todos de clase, sin facade module-level) no encontro el patron visto
en `inventario`.

## FASE 1 — Reglas de negocio (clasificadas)

| Regla | Clasificacion | Evidencia |
|---|---|---|
| `_generar_salida_inventario()` se dispara SOLO tras facturar exitosamente -- si el Kardex falla, la venta+factura completas se revierten (transaccion atomica) | **CRITICAL** | Verificado en la mision anterior (test F23 `test_stock_insuficiente_revierte_venta_y_factura_completas`) |
| El costo del movimiento de salida usa `producto.costo_promedio`, NUNCA `precio_unitario` de venta | **CRITICAL** | Test F23 dedicado, ya verificado |
| DTO UBL 2.1 se construye una sola vez (`_construir_dto_factura()`), consumido por CUFE/XML/firma -- un solo punto de verdad para el documento fiscal | **CRITICAL** | `business_service.py:218` |
| Reintentar `_generar_salida_inventario()` no duplica movimientos (idempotente) | **IMPORTANT** | Test F23 dedicado |
| Items de tipo Servicio NO generan movimiento de inventario | **IMPORTANT** | Test F23 dedicado |
| `_tax_level_code_emisor`/`_tax_level_code_receptor` traducen regimen tributario/tipo de documento a codigos DIAN especificos | **IMPORTANT** | Logica normativa de mapeo, parte del DTO UBL |

## FASE 2 — Mapa de dominio

Sin cambios respecto a la auditoria previa (`ResolucionFacturacion`,
`Venta`, `ItemVenta`).

## FASE 6 — ORM/BD: verificacion N+1

`VentaSelector`: `select_related` (cliente/proyecto/factura_asociada/
resolucion) en list Y detail, mas `prefetch_related("items",
"items__producto", "items__servicio")` en detail -- evita N+1 incluso
en el traversal anidado item->producto/servicio. `crud_service.py`
usa `bulk_create()` para items (no loop de `.save()`). **Sin
hallazgos de N+1.**

## FASE 12/13 — Codigo muerto / duplicacion

Barrido fresco: 15 metodos en `business_service.py`, todos dentro de
clase (`VentaBusinessService`/`ResolucionFacturacionBusinessService`),
**sin funciones module-level sueltas**. Mismo patron limpio que
`compras`. **Sin hallazgos nuevos.**

## Normativa (FASE 14)

Sin cambios respecto a la mision anterior: el hallazgo P1
(transmision DIAN) fue verificado y documentado con evidencia
completa en `facturas` (no en `ventas`, que solo orquesta el
pre-proceso). `ResolucionFacturacion.clean()` no ejecutandose en
`bulk_create()`/ORM directo sigue como deferred P2 conocido (sin
`CheckConstraint` DB), no se corrige en esta pasada (requiere
migracion, evaluar en una sesion dedicada a cierre de deuda tecnica).

## Cambios realizados en esta pasada

**Ninguno.**

## FASE 22 — Release Gate

- [x] Reglas de negocio clasificadas
- [x] Mapa de dominio (sin cambios)
- [x] N+1 verificado -- `select_related`/`prefetch_related` anidado + `bulk_create` consistentes
- [x] Codigo muerto -- barrido fresco, sin hallazgos nuevos
- [x] Sin cambios de codigo -> sin necesidad de validacion adicional

**APP = COMPLETED.**
