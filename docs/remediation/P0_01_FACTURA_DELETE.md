# P0-01 — Facturas sin hard-delete destructivo

**Estado:** VERIFIED
**App propietaria:** `facturas`
**Fecha:** 2026-08-28 (corregido) / 2026-08-28 (re-verificado, esta pasada)

## Hallazgo

`FacturaViewSet.destroy()` permitía eliminar físicamente cualquier
`Factura` sin importar su estado — incluyendo facturas `ACEPTADA` con
CUFE reconocido por la DIAN y con `AsientoContable` ya extraído por
Contabilidad. Un `DELETE` dejaba el asiento contable huérfano
(`documento_origen_id` apuntando a una fila que ya no existe) y
destruía evidencia fiscal/documental sin dejar rastro.

## Causa raíz

Ausencia de guard de estado en el Service Layer:
`FacturaCRUDService.eliminar()` se invocaba directamente desde
`FacturaServiceMixin.service_eliminar()` sin ninguna validación previa
de negocio.

## Corrección (capa propietaria: `facturas`)

Ver matriz completa de estados en `P0_01_FACTURA_DELETE_MATRIX.md`.

- `FacturaBusinessService.eliminar_factura()` (nuevo, `@transaction.atomic`):
  bloquea el `DELETE` salvo `factura.estado == BORRADOR`. Reutiliza el
  mecanismo de anulación YA EXISTENTE (`cambiar_estado()` →
  `TRANSICIONES_VALIDAS`, alcanza `ANULADA` desde todo estado no
  terminal) como única vía sancionada para "eliminar" una factura con
  impacto — no se creó un estado ni un mecanismo nuevo.
- `FacturaServiceMixin.service_eliminar()`: ahora llama a
  `eliminar_factura()` en vez de al CRUD directo.
- `FacturaViewSet.destroy()`: captura `ValidationError` → HTTP 400 (antes
  cualquier excepción no capturada caía al handler genérico → 500,
  ocultando el motivo real detrás de un error de servidor).

## Preservación de trazabilidad

La anulación (`ANULADA`) **no borra la factura** — conserva: número,
CUFE, XML/documento origen, relaciones a `ItemFactura`, `Retencion`,
`ImpuestoDocumento`, `TransmisionFactura`, y el vínculo a `Venta`
(`factura_asociada`). Solo `BORRADOR` (sin CUFE, nunca transmitida) se
elimina físicamente — exactamente el caso sin ningún impacto documental.

## Impacto cross-app verificado (no modificado automáticamente — regla del plan)

Anular una `Factura ACEPTADA` **no dispara** una reversa automática de:

- `AsientoContable` (Contabilidad) — permanece como fue extraído.
- `MovimientoInventario` (Inventario) — permanece.
- Conciliación bancaria (Bancos) — no se toca.

Esto es una decisión de alcance explícita, no un descuido: implementar
la reversa automática cross-app requeriría diseñar el contrato de
reversa en cada dominio propietario (`Contabilizador.reversar_asiento()`
ya existe como patrón, pero activarlo automáticamente desde `facturas`
violaría la regla de capa propietaria si se hace sin que Contabilidad lo
exponga como un servicio explícito para este trigger). Documentado como
deuda pendiente, no como parte de este hallazgo P0.

## Tests (DB-level, no solo HTTP)

`apps/tenant/facturas/tests/test_remediation_p0_01_delete_guard.py` — 6
tests, cada uno confirma **estado real de BD** además del código HTTP
(`Factura.objects.filter(id=...).exists()` / `refresh_from_db()`), no
solo el status code:

1. `BORRADOR` → `DELETE` → 204 + fila ausente en BD.
2. `ENVIADA` → `DELETE` → 400 + fila **presente** en BD.
3. `ACEPTADA` → `DELETE` → 400 + fila presente.
4. `RECHAZADA` → `DELETE` → 400 + fila presente.
5. `ANULADA` → `DELETE` → 400 + fila presente.
6. `ACEPTADA` → anulación vía `cambiar-estado` → 200 + `factura.estado == ANULADA` tras `refresh_from_db()`.

## Evidencia

Corrida local (previa, re-confirmada sin cambios de código en esta
pasada): 12/12 PASS (6 nuevos + 6 regresión `test_scope_facturas_f11.py`),
1735.23s.

## Antes / Después

| | Antes | Después |
|---|---|---|
| `DELETE` sobre factura `ACEPTADA` | 204, fila eliminada físicamente, asiento contable huérfano | 400, fila intacta |
| `DELETE` sobre factura `BORRADOR` | 204, fila eliminada | 204, fila eliminada (sin cambio — comportamiento correcto ya existía) |
| Manejo de excepción en `destroy()` | Caía a 500 genérico | 400 con mensaje explicando el motivo |

## Riesgos / deuda pendiente

Reversa automática cross-app de `AsientoContable`/`MovimientoInventario`
al anular una factura `ACEPTADA` — no implementada, requiere diseño
dedicado en la capa propietaria de cada dominio (Contabilidad,
Inventario), fuera del alcance mínimo de este hallazgo P0.
