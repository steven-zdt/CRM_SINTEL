# APP_ventas_NORMATIVE_MATRIX — Matriz normativa colombiana

Parte de `documentacion/audits/apps/APP_ventas_AUDIT.md` (FASE M).

## Alcance real de `ventas` en la cadena de facturacion DIAN

`ventas` orquesta el pre-proceso de facturacion (DTO canonico UBL 2.1,
asignacion de consecutivo) pero **delega la implementacion tecnica DIAN
a `apps/tenant/facturas/services/dian/*`**: `CufeService.calcular_
desde_dto()` (calculo de CUFE), `UBL21BuilderService.build()` (XML
UBL 2.1), y firma XAdES-EPES (confirmado en
`business_service.py:576-592`). La correccion criptografica/schema de
esos servicios **se auditara en `facturas`** (app 14/16 de esta
mision) -- aqui solo se audita lo que es responsabilidad real de
`ventas`: la gestion de `ResolucionFacturacion` (rangos autorizados,
vigencia, consecutivo atomico).

## Matriz

| # | Obligacion | Sujeto obligado | Supuesto de hecho | Norma | Evidencia | Aplicabilidad |
|---|---|---|---|---|---|---|
| 1 | Emitir facturas de venta dentro de un rango de numeracion autorizado por resolucion DIAN vigente | Empresa (emisor) | Toda venta facturada (`estado -> FACTURADA_DIAN`) | Normativa de facturacion electronica DIAN (numeracion autorizada) -- resolucion especifica configurable por tenant, no hardcodeada (correcto) | `models.py` (`ResolucionFacturacion`), `business_service.py:96-113` (`select_for_update()` + verificacion `esta_en_rango()`) | **OBLIGATORIO** -- implementado con concurrencia segura |
| 2 | Vigencia temporal de la resolucion (`fecha_desde`/`fecha_hasta`) | Empresa (emisor) | Toda venta facturada | Igual a #1 | `models.py: esta_vigente_en_fecha()` | **OBLIGATORIO** -- metodo existe. **REQUIERE_VALIDACION**: el propio `.agent/` doc de la app (linea 79) ya documenta que `clean()` (que valida `rango_desde <= rango_hasta`) "no se ejecuta automaticamente en `bulk_create()` o inserciones ORM directas" y recomienda un `CheckConstraint` DB pendiente -- hallazgo preexistente, no nuevo, se re-confirma vigente en esta auditoria (ver Deferred). |
| 3 | CUFE (Codigo Unico de Facturacion Electronica) | Empresa (emisor) | Toda venta facturada | Resolucion DIAN de facturacion electronica (calculo criptografico especifico) | Delegado a `facturas.services.dian.cufe.CufeService` | **FUERA DE ALCANCE de `ventas`** -- se audita en `facturas` |
| 4 | XML UBL 2.1 + firma XAdES-EPES | Empresa (emisor) | Toda venta facturada | Estandar UBL 2.1 + politica de firma XAdES exigida por DIAN | Delegado a `facturas.services.dian.ubl21_builder`/`AttachedDocumentService` | **FUERA DE ALCANCE de `ventas`** -- se audita en `facturas` |
| 5 | IVA por item (`porcentaje_iva`) | Empresa (emisor) | Cada `ItemVenta` | Estatuto Tributario, tarifas de IVA -- sin articulo citado en codigo | `business_service.py:331`, `models.py:266` | **REQUIERE_VALIDACION** -- mismo patron que `compras`: entrada libre del usuario, sin validacion contra tarifas vigentes (0%/5%/19%). A diferencia de compras, aqui SI se traduce en un documento fiscal real (Factura DIAN), por lo que el riesgo es mayor que en una orden de compra interna. |

## Deferred

| # | Item | Prioridad |
|---|---|---|
| 1 | `ResolucionFacturacion.clean()` (valida `rango_desde <= rango_hasta`) no se ejecuta en `bulk_create()`/insercion ORM directa -- ya documentado en el `.agent/` doc propio (2026-06-18) como pendiente de `CheckConstraint` DB, re-confirmado vigente | P2 (integridad de datos, no bloqueante en flujo normal via API/serializer que si invoca `full_clean()`) |
| 2 | `porcentaje_iva` en `ItemVenta` sin validar contra tarifas de IVA vigentes -- mismo hallazgo que `compras`, pero aqui el documento resultante SI es una factura DIAN real | P2 (mayor prioridad que el equivalente en compras, por ser documento fiscal) |
| 3 | Correccion tecnica de CUFE/UBL2.1/XAdES -- fuera de alcance de `ventas`, se revisara con evidencia completa al auditar `facturas` | Ver auditoria de `facturas` (app 14/16) |
