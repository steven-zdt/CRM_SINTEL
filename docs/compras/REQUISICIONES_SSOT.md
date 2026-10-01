# REQUISICIONES_SSOT.md — Matriz de propiedad de datos

| Concepto | SSoT real | Requisicion solo... |
|---|---|---|
| Necesidad / solicitante / justificacion / prioridad | **Requisiciones** (este submodulo) | — |
| Proyecto | `apps.tenant.proyectos.Proyecto` | referencia FK (0..1), nunca copia campos |
| Cotizacion comercial (venta a cliente) | `apps.tenant.cotizaciones.Cotizacion` | referencia via `RequisicionCotizacion` (contexto/trazabilidad, nunca reinterpretada como cotizacion de proveedor) |
| Proveedor | `apps.tenant.proveedores.Proveedor` | resuelto por `OrdenCompraBusinessService`, la Requisicion nunca lo referencia directo |
| Orden de Compra / Recepcion | `apps.tenant.compras` (existente) | `OrdenCompra.requisicion` FK real (1:N), Requisicion nunca crea/edita una OC directamente — delega a `OrdenCompraBusinessService` |
| Stock / Kardex | `apps.tenant.inventario` | Requisicion nunca toca stock — el flujo real es Requisicion -> OrdenCompra -> RecepcionCompra -> MovimientoInventario |
| Factura fiscal (DIAN) | `apps.tenant.facturas.Factura` | referencia via `RequisicionFactura` o `RequisicionDocumento` (placeholder externo); nunca duplica CUFE/subtotal/IVA/total/estado DIAN |
| Cuentas por Pagar | `apps.tenant.proveedores` (`CuentasPagarBusinessService`) | fuera del alcance de Requisiciones — el bridge vive integro en `OrdenCompraBusinessService._sincronizar_cuenta_por_pagar()`, sin cambios |
| Centro de Costo | **No existe una entidad real** (ver `REQUISITION_BASELINE.md` #2) | se usa `proyecto` como agrupador — campo `centro_costo` DEFERRED, nunca inventado |
| Documentos internos/externos no fiscales | `RequisicionDocumento` (este submodulo) | SSoT propio — soft reference (`documento_uuid` opcional) para soportar evidencia aun no reconciliada |

## Regla de oro aplicada

Antes de cada campo/FK nuevo en este submodulo se verifico: ¿ya existe en otro dominio? -> reusar (Proyecto, Proveedor, Factura, Cotizacion, OrdenCompra). ¿El dominio no existe? -> marcar DEFERRED, nunca inventar (CentroCosto). Ningun campo de este submodulo duplica de forma permanente un dato que otro dominio ya posee como SSoT, salvo snapshots explicitamente justificados (ninguno fue necesario en esta implementacion).
