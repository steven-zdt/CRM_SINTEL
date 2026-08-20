# APP_compras_NORMATIVE_MATRIX — Matriz normativa colombiana

Parte de `documentacion/audits/apps/APP_compras_AUDIT.md` (FASE M).

## Hallazgo principal: `compras` es workflow de Ordenes de Compra, sin logica de retencion

A diferencia de `proveedores` (que SI calcula Retefuente/ReteICA),
`apps/tenant/compras` gestiona el **ciclo de vida de la Orden de
Compra** (BORRADOR -> PENDIENTE -> APROBADA -> RECIBIDA/ANULADA) --
proveedor, items, IVA por linea, totales, aprobacion. **Confirmado con
grep repo-wide: cero referencias a `retefuente`/`reteica`/`reteiva`/
`retencion` en todo `apps/tenant/compras/`.** No hay calculo ni
configuracion de retenciones en esta app -- eso vive en `proveedores`
(config) y, segun el hallazgo pendiente de esa auditoria, potencialmente
en `gastos` (aun sin confirmar).

## Matriz

| # | Obligacion | Sujeto obligado | Supuesto de hecho | Norma | Evidencia | Aplicabilidad |
|---|---|---|---|---|---|---|
| 1 | IVA por item de orden de compra (`porcentaje_iva`) | Proveedor (factura) / Empresa (registra) | Cada `ItemOrdenCompra` | Estatuto Tributario, tarifas generales de IVA (19% general, tarifas diferenciales 5%/0% segun bien/servicio) -- **sin articulo especifico citado en codigo** | `crud_service.py:133,203` (`porcentaje_iva = Decimal(str(item_data.get('porcentaje_iva', 0)))`) | **REQUIERE_VALIDACION** -- el campo es entrada libre del usuario (default 0), sin validacion de que el porcentaje ingresado corresponda a una tarifa de IVA vigente valida en Colombia (0%, 5%, 19%). Riesgo bajo (es un campo de captura manual en un documento interno -- orden de compra -- no una liquidacion tributaria automatica), pero podria permitir capturar tarifas invalidas sin aviso. |
| 2 | Consecutivo de orden de compra dentro de rango autorizado por plantilla | Empresa (control interno) | Creacion de `OrdenCompra` con `plantilla` asignada | Control interno, no normativa DIAN (las Ordenes de Compra no son documentos fiscales electronicos, a diferencia de facturas/notas credito) | `business_service.py:129-134` (`select_for_update()` + `F('consecutivo_actual') + 1`) | **NO_APLICA normativa DIAN** -- es un control de negocio propio (numeracion interna), no una obligacion legal. Implementado correctamente (concurrency-safe). |

## Conclusion FASE M

`compras` no requiere items normativos de alta prioridad. El unico
punto de atencion (validacion de tarifas IVA validas en el campo
`porcentaje_iva`) es de riesgo bajo dado que es un documento interno
(orden de compra), no una declaracion tributaria automatica -- se
registra como deferred de baja prioridad.

**Deferred:**

| # | Item | Prioridad |
|---|---|---|
| 1 | `porcentaje_iva` en `ItemOrdenCompra` no valida contra tarifas de IVA vigentes (0%/5%/19%) -- entrada libre del usuario | P3 |
