# REQUISICIONES_FLOW.md

## Flujo principal (feliz)

```
Usuario (Solicitante)
  -> Nueva Requisicion (BORRADOR) -- items + justificacion + proyecto opcional
  -> Enviar a Aprobacion (PENDIENTE_APROBACION) -- exige justificacion no vacia
  -> Responsable aprueba (APROBADA) -- cantidad_aprobada = cantidad_solicitada por item
  -> Generar Orden de Compra -- selecciona plantilla+proveedor+items+cantidades
       -> OrdenCompraBusinessService.crear_orden_compra() crea la OC real (BORRADOR)
       -> RequisicionCompraItem.cantidad_ordenada se acumula
       -> Requisicion pasa a EN_PROCESO_COMPRA (primera orden) automaticamente
  -> (Si quedan items pendientes) se puede generar otra OC adicional
       -> Requisicion pasa a PARCIALMENTE_ATENDIDA
  -> Cuando todo item.cantidad_ordenada+cancelada >= cantidad_aprobada
       -> Requisicion pasa a ATENDIDA automaticamente (recalcular_estado())
```

## Flujo de rechazo

```
PENDIENTE_APROBACION -> Rechazar (motivo obligatorio) -> RECHAZADA (estado terminal)
```

## Flujo de cancelacion

```
BORRADOR|PENDIENTE_APROBACION|APROBADA|EN_PROCESO_COMPRA|PARCIALMENTE_ATENDIDA
  -> Cancelar (motivo opcional) -> CANCELADA (estado terminal)
```

## Trazabilidad (UI de solo lectura + vinculos manuales)

- `RequisicionDocumento`: adjuntar evidencia/archivos (incluye placeholders de documentos externos aun no reconciliados: `tipo=FACTURA`, `documento_uuid=NULL`, `numero_referencia="FE-12345"`).
- `RequisicionCotizacion`/`RequisicionFactura`: vinculo manual a una Cotizacion/Factura YA EXISTENTE, solo de contexto — nunca dispara efectos de negocio.
- `ordenes_compra` (reverse FK): lista real de OC generadas, visible en el detalle.
- `historial_estados`: append-only, cada transicion queda registrada con usuario/motivo/timestamp.

## Verificacion end-to-end realizada (Fase 6, evidencia real)

Ejecutada contra el tenant real `admin` (Sintel Tecnology SAS) via Playwright, sesion inyectada para el usuario QA existente `qa_datatables_pilot`:

1. Crear requisicion `REQ-000001` (1 item, $150,000 total estimado) -- OK, sin errores de consola/red.
2. Enviar a aprobacion -- estado -> `PENDIENTE_APROBACION` -- OK.
3. Aprobar -- estado -> `APROBADA`, item `cantidad_aprobada=3` (igual a solicitada) -- OK.
4. Panel "Generar Orden de Compra" -- item pendiente=3 precargado, plantilla/proveedor cargados via AJAX -- OK.
5. Confirmar generacion -- OC creada (BORRADOR, $150,000), `cantidad_ordenada` del item pasa a 3, requisicion transiciona automaticamente `APROBADA -> EN_PROCESO_COMPRA -> ATENDIDA` en el mismo paso (pendiente llego a 0) -- OK, visible en el listado con badge "ATENDIDA".

0 errores de consola, 0 requests fallidos en las 3 corridas del smoke test. Datos de prueba eliminados despues de la verificacion (la `RequisicionCompra` y la `OrdenCompra` generada, via `manage.py shell` scoped a `schema_context('admin')`).

**Bug real encontrado y corregido durante esta verificacion:** ver `REQUISICIONES_ARCHITECTURE.md` #9 (orden de registro de URLs) y `REQUISICIONES_PRE_TEST_AUDIT.md` (selector con campos inexistentes en `TenantProfile`).
