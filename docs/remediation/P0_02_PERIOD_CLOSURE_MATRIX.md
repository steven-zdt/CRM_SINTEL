# P0_02_PERIOD_CLOSURE_MATRIX

Matriz de operaciones vs. estado del `PeriodoContable` cuya
`fecha_inicio`/`fecha_fin` contiene la fecha relevante del documento
(`fecha_emision` en Factura, `fecha` en Gasto).

| operación | período abierto | período cerrado | permitido | bloqueado | excepción | owner |
|---|---|---|---|---|---|---|
| `PATCH` Factura (`actualizar_factura_limitado`) | Sí | No | Edición normal | 400 si `fecha_emision` cae en período cerrado | Ninguna — el plan explícitamente prohíbe inventar excepciones sin evidencia | `facturas` (consumidor), `verificar_periodo_cerrado()` en `contabilidad` (owner del concepto) |
| `cambiar_estado` Factura → `ANULADA` | Sí | No | Anulación normal | 400 si `fecha_emision` cae en período cerrado | Ninguna | `facturas` / `contabilidad` |
| `cambiar_estado` Factura → otros (`ENVIADA`, `ACEPTADA`, `RECHAZADA`, `ERROR_TRANSMISION`) | Sí | Sí (no validado) | Siempre | Nunca | Deliberada — son transiciones del ciclo administrativo de sincronización con el portal DIAN (reflejan una respuesta externa ya ocurrida), no una "edición de negocio" retroactiva sobre el resultado del período; el propio docstring de `PeriodoContable` solo promete bloquear "edición/anulación" | `facturas` |
| `PATCH`/edición de Gasto (`GastoViewSet.perform_update`) | Sí | No | Edición normal | 400 si la fecha actual **o** la nueva fecha (si cambia) cae en período cerrado | Ninguna | `gastos` (consumidor), `contabilidad` (owner) |
| Anular Gasto (`GastoBusinessService.anular_gasto`) | Sí | No | Anulación normal | Rechazado si `documento.fecha` cae en período cerrado | Ninguna | `gastos` / `contabilidad` |
| `CREATE` Factura/Gasto con fecha en período ya cerrado | Sí (n/a) | Sí (no bloqueado) | Siempre se permite crear | Nunca | Deliberada — bloquear `CREATE` arriesgaría romper flujos legítimos de importación/backfill histórico no verificados en esta corrección; el docstring de `PeriodoContable` promete "edición/anulación", no "creación" | Sin owner de bloqueo — decisión documentada, no un gap |
| Cierre del propio período (`cerrar_periodo`) | Sí (permitido si checklist limpio — ver P1-05) | No aplica (ya cerrado) | Con checklist limpio | Con pendientes/descuadres (P1-05, fuera del alcance P0-02) | N/A | `contabilidad` |

## Regla de owner confirmada

`verificar_periodo_cerrado()` — **una sola función, propiedad de
`contabilidad`** — es invocada por lectura desde `facturas` y `gastos`
(nunca reimplementada ni duplicada en el consumidor). Ningún consumidor
importa el modelo `PeriodoContable` para calcular el cierre por su
cuenta.
