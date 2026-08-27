# Cotizaciones — Flujo End-to-End Verificado (FASE 50)

**Fecha:** 2026-08-27
**Método:** verificación real contra el tenant `home` vía API con JWT real (el navegador sandbox de esta sesión no pudo completar login contra este dominio — ver nota al final), confirmando también estado en base de datos, no solo la respuesta HTTP.

---

## Escenario ejecutado

```
Cliente (real, "Atlas")
   ↓
Cotización (POST, con fecha_emision explícita)
   ↓
Item (PRODUCTO, cantidad=2, costo=500, utilidad=10%)
   ↓
Totales (calculados por backend: 1309.00)
   ↓
Editar (PATCH dias_totales)
   ↓
Eliminar (DELETE, sin Factura vinculada → permitido)
   ↓
Verificado 404 tras eliminar (confirmado en BD, no solo HTTP)
```

## Resultado real (10/10 operaciones OK, ejecutado hoy)

| Paso | Endpoint | Resultado |
|---|---|---|
| CREATE Cotización + item | `POST /api/v1/cotizaciones/` | `201`, `total_con_impuestos=1309.00` correcto |
| READ list | `GET /api/v1/cotizaciones/` | `200` |
| READ detail | `GET /api/v1/cotizaciones/{uuid}/` | `200`, item presente con `subtotal_linea=1100.00` |
| UPDATE | `PATCH /api/v1/cotizaciones/{uuid}/` | `200`, campo actualizado, totales intactos |
| DELETE (sin Factura) | `DELETE /api/v1/cotizaciones/{uuid}/` | `204` |
| Verificación post-DELETE | `GET /api/v1/cotizaciones/{uuid}/` | `404` |

Adicionalmente, en la misma sesión de verificación:
- **DELETE bloqueado correctamente** cuando existe una Factura vinculada vía `Factura.cotizacion_uuid` (test real, `test_delete_and_constraints.py`).
- **ConfiguracionCotizacion (Plantilla/Config)**: CRUD completo (create/read list/read detail/update/delete/verificar-eliminado) — 5/5 OK.
- **Bug de creación reportado por el usuario** (415 Unsupported Media Type): reproducido exactamente con `Content-Type: text/plain` (lo que el navegador mandaba antes del fix), confirmado resuelto con `Content-Type: application/json`.
- **Bug de grilla Tabulator** ("Expecting: array, Received: object"): causa raíz confirmada (Tabulator crudo sin traducir la paginación de DRF) y corregida usando el `TabulatorFactory` compartido.
- **Nuevo endpoint de edición de Producto** (`render-offcanvas/editar`, agregado hoy): verificado en vivo, `200`, formulario pre-poblado correctamente con los datos reales del Producto.
- **Bug de locale encontrado y corregido durante esta misma verificación**: el `value` del campo `precio_venta` se renderizaba con coma decimal (`100,00`, formato es-CO) en vez de punto, lo que habría invalidado un `<input type="number">` — corregido con `stringformat:"s"` (sin formateo de locale).

## Qué NO se pudo verificar visualmente

El navegador sandbox de esta sesión (`Claude Browser`) no pudo completar el login contra `home.sintel.net.co` (`ERR_BLOCKED_BY_CLIENT` a nivel de red, no relacionado con credenciales ni con el código). `Claude in Chrome` (navegador real) tampoco pudo resolver ese dominio (solo es alcanzable desde dentro del entorno Docker del proyecto). Por esto, toda la verificación de esta misión es a nivel de API/backend + inspección de código real del frontend, no clics reales de UI. Se documenta esto honestamente en vez de asumir que "probablemente funciona" — quien revise este documento debería hacer al menos una pasada visual manual antes de considerar el frontend 100% verificado.
