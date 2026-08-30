# P0_01_FACTURA_DELETE_MATRIX

Matriz de eliminación de `Factura` — estados reales de
`Factura.Estado` (`apps/tenant/facturas/models.py:26-36`), sin estados
inventados.

| estado | puede_delete | puede_anular | puede_reversar | impacto_fiscal | impacto_contable | impacto_banco | impacto_inventario | acción correcta |
|---|---|---|---|---|---|---|---|---|
| `BORRADOR` | **Sí** (hard-delete físico, `eliminar_factura()`) | Sí (a `ANULADA`, no-op práctico ya que nunca fue transmitida) | No aplica — nunca hubo asiento/movimiento que reversar | No — nunca transmitida a DIAN, sin CUFE | No — `ExtractorFacturas` solo extrae `estado='ACEPTADA'` (`apps/tenant/contabilidad/integracion/extractores/facturas.py:52,71`) | No — ninguna conciliación posible sobre un borrador | No — `VentaBusinessService._generar_salida_inventario()`/pipeline de NC solo corren sobre facturas ya persistidas con flujo completo, no sobre borradores sueltos | `DELETE` físico permitido y correcto |
| `ENVIADA` | **No** | Sí (a `ANULADA`) | No — aún sin `AsientoContable` (extractor exige `ACEPTADA`) | Sí — ya fue transmitida (tiene `TransmisionFactura`), aunque sin respuesta aceptada aún | No — todavía no extraída | Posible si ya se generó CxC/CxP anticipada — no verificado como bloqueante en esta corrección (fuera de alcance) | No — sin recepción/venta consolidada aún si el flujo lo exige | `ANULACIÓN` vía `cambiar_estado()`, nunca `DELETE` |
| `ACEPTADA` | **No** | Sí (a `ANULADA`) | Sí, pero **no automática** — el `AsientoContable`/`MovimientoInventario` ya extraídos NO se revierten solos al anular (deuda documentada, ver `P0_01_FACTURA_DELETE.md` §Riesgos) | **Sí** — CUFE reconocido por la DIAN, documento fiscal válido | **Sí** — es el único estado que el extractor de Contabilidad toma (`estado='ACEPTADA'`) | Sí — candidata a conciliación bancaria real | Sí — dispara `ENTRADA_DEVOLUCION`/`SALIDA_VENTA` según el pipeline de Kardex | `ANULACIÓN` únicamente. `DELETE` físico bloqueado por `eliminar_factura()` |
| `RECHAZADA` | **No** | Sí (a `ENVIADA` para reintentar, o a `ANULADA`) | No — la DIAN rechazó, nunca hubo extracción contable (no es `ACEPTADA`) | Sí — hubo un intento real de transmisión con respuesta de la DIAN | No | No | No | `ANULACIÓN` o reintento (`ENVIADA`), nunca `DELETE` |
| `ERROR_TRANSMISION` | **No** | Sí (a `ENVIADA` para reintentar, o a `ANULADA`) | No — nunca hubo respuesta de la DIAN, sin extracción contable | Parcial — intento fallido antes de respuesta (timeout/adaptador no configurado), no es un rechazo fiscal formal pero sí evidencia de intento | No | No | No | `ANULACIÓN` o reintento (`ENVIADA`), nunca `DELETE` |
| `ANULADA` | **No** | No — es terminal (`TRANSICIONES_VALIDAS['ANULADA'] = set()`) | Depende del estado previo (ver arriba) — el registro de anulación en sí no es reversable | Igual al estado que tenía antes de anular (el impacto fiscal no desaparece por anular) | Igual al estado previo — el asiento generado (si lo hubo) permanece | Igual al estado previo | Igual al estado previo | Ninguna acción adicional — estado terminal |

## Regla aplicada (confirmada contra el modelo real, no inventada)

```
documento sin impacto  (BORRADOR)
    → delete físico controlado

documento con impacto  (ENVIADA, ACEPTADA, RECHAZADA, ERROR_TRANSMISION)
    → NO hard delete — solo ANULACIÓN vía cambiar_estado()

documento fiscal procesado (ACEPTADA)
    → ANULACIÓN (el único mecanismo de "reversa" a nivel de estado;
      la reversa contable/inventario real queda fuera de esta corrección,
      documentada como deuda)
```

Esto corresponde exactamente a la implementación real de
`eliminar_factura()`: `if factura.estado != Factura.Estado.BORRADOR: raise`.
Ningún estado se inventó — los 6 son los únicos definidos en
`Factura.Estado`.
