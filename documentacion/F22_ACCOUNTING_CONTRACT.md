# F22 — Contrato Contable Inventario -> Contabilidad

**Fecha:** 2026-08-09

## 1. Matriz de movimientos (validada contra codigo real, no hipotesis)

| `MovimientoInventario.tipo` | Contabilizable | `TipoTransaccion` | Motivo / evidencia |
|---|---|---|---|
| `ENTRADA_COMPRA` | Si | `COMPRA_INVENTARIO` | Aumenta el activo Inventario; unico tipo con datos reales garantizados hoy (F21) |
| `SALIDA_VENTA` | Si (mecanismo listo, sin datos reales aun) | `SALIDA_INVENTARIO_VENTA` | Genera costo de venta. Ver `F22_INVENTARIO_BASELINE.md` §4: `ventas`/`facturas` no generan este tipo todavia — brecha preexistente, no de F22 |
| `ENTRADA_AJUSTE` | Si | `AJUSTE_INVENTARIO` (concepto `INGRESO_AJUSTE_INVENTARIO`) | Sobrante de inventario — variacion economica real |
| `SALIDA_BAJA` | Si | `BAJA_INVENTARIO` (concepto `GASTO_DETERIORO_INVENTARIO`) | Perdida/deterioro — gasto real |
| `SALIDA_CONSUMO` | Si | `BAJA_INVENTARIO` (concepto `GASTO_CONSUMO_INTERNO`) | Consumo interno — gasto real, mismo `tipo_transaccion` que `SALIDA_BAJA` pero concepto distinto (ambos ya seedeados por separado, ver §2) |
| `ENTRADA_DEVOLUCION` | Si | `AJUSTE_INVENTARIO` (concepto `COSTO_VENTA_DEVOLUCION`) | Devolucion de cliente: reversa parcial del costo de venta ya reconocido. Concepto ya seedeado (`seed_reglas_contables.py`, "Ajuste al costo por devolucion") — no inventado para F22 |
| `TRASLADO_SALIDA` | **No** | — | Transferencia interna entre sedes de la misma empresa — no es una transaccion economica externa (§5) |
| `TRASLADO_ENTRADA` | **No** | — | Idem |
| `ASIGNACION_RESPONSABLE`, `TRASLADO_MANTENIMIENTO`, `RETORNO_MANTENIMIENTO`, `SALIDA_BAJA_ACTIVO` | Fuera de alcance F22 | — | Movimientos de `ActivoFijo`, no de `Producto` — el diagrama completo de F22 (§22.46 del prompt maestro) es especificamente Compras->Recepcion->Inventario->Kardex, dominio de mercancia, no de activos fijos. Documentado como deuda separada, no fabricado |

La hipotesis inicial del prompt maestro (§9) coincidia en espiritu; la diferencia real encontrada:
`AJUSTE_ENTRADA`/`AJUSTE_SALIDA` (nombres del prompt) no existen como tal — los enums reales son
`ENTRADA_AJUSTE`/`SALIDA_BAJA`/`SALIDA_CONSUMO`/`ENTRADA_DEVOLUCION` (mas granular). Se uso el enum
real, no se crearon tipos nuevos.

## 2. `ReglaContable` ya seedeadas (verificadas, no reinventadas)

`apps/tenant/contabilidad/management/commands/seed_reglas_contables.py` (idempotente,
`get_or_create`):

| `tipo_transaccion` | `concepto` | `cuenta_codigo` | Lado en la linea |
|---|---|---|---|
| `COMPRA_INVENTARIO` | `INVENTARIO_PRODUCTO` | 143505 | DEBE |
| `COMPRA_INVENTARIO` | `PASIVO_COMPRA_INVENTARIO` | 220505 | HABER |
| `SALIDA_INVENTARIO_VENTA` | `COSTO_VENTA_PRODUCTO` | 613501 | DEBE |
| `SALIDA_INVENTARIO_VENTA` | `INVENTARIO_PRODUCTO` | 143505 | HABER |
| `BAJA_INVENTARIO` | `GASTO_DETERIORO_INVENTARIO` | 529901 | DEBE |
| `BAJA_INVENTARIO` | `GASTO_CONSUMO_INTERNO` | 519595 | DEBE |
| `BAJA_INVENTARIO` | `INVENTARIO_PRODUCTO` | 143505 | HABER |
| `AJUSTE_INVENTARIO` | `INVENTARIO_PRODUCTO` | 143505 | DEBE (entrada) / HABER (salida) |
| `AJUSTE_INVENTARIO` | `INGRESO_AJUSTE_INVENTARIO` | 425050 | HABER |
| `AJUSTE_INVENTARIO` | `COSTO_VENTA_DEVOLUCION` | 613501 | HABER |

**Nota de higiene de datos encontrada (no corregida, fuera de alcance quirurgico de F22):**
`seed_reglas_contables.py` tiene un segundo bloque duplicado para `AJUSTE_INVENTARIO`
(`INVENTARIO_MERCANCIAS`/`AJUSTE_INVENTARIO_INGRESO`/`GASTO_BAJA_INVENTARIO`, mismos codigos PUC,
nombres de concepto distintos) — ambos bloques coexisten sin conflicto porque
`ResolverCuentas.resolver_cuenta()` filtra por `concepto` exacto (`.first()`, sin ambiguedad por
nombre). F22 usa consistentemente los nombres de la tabla de arriba (primer bloque, el que
tambien comparte convencion de nombres con `COMPRA_INVENTARIO`/`SALIDA_INVENTARIO_VENTA`/
`BAJA_INVENTARIO`). No se borra el bloque duplicado — es codigo preexistente ajeno a F22 y
tocarlo no es necesario para que el extractor funcione correctamente.

**Consecuencia real:** si un tenant no ha corrido `seed_reglas_contables`, el extractor fallara
con `ReglaContableNoDefinidaError` por documento (aislado, no tumba el batch) — comportamiento
correcto del framework existente, no un bug de F22.

## 3. `TerceroSnapshot` — resolucion real, no generica

`TransaccionEconomica.tercero` es obligatorio (`TerceroSnapshot`, sin default). Decision por tipo:

- **`ENTRADA_COMPRA`**: se resuelve el `Proveedor` real recorriendo el mismo soft-reference que
  F21 ya usa para idempotencia: `MovimientoInventario.documento_origen_id` ->
  `compras.RecepcionCompraItem` -> `.recepcion.orden_compra.proveedor`. Este es un import de
  lectura de `contabilidad` hacia `compras` — arquitectonicamente identico al patron ya existente
  (`ExtractorGastos` importa `gastos.models`, `ExtractorNomina` importa `empleados.models`):
  Contabilidad SIEMPRE puede leer de cualquier app fuente en el modelo Pull; lo prohibido es el
  sentido inverso. Si la cadena no resuelve (movimiento sin `documento_origen_id`, registro
  historico, o entrada manual futura sin recepcion), se usa un tercero generico
  (`TipoTercero.OTRO`, `id_origen=movimiento.producto_id`, `nit=''`,
  `razon_social='Movimiento de inventario sin proveedor asociado'`) — nunca se bloquea la
  contabilizacion por falta de tercero, pero tampoco se inventa un NIT falso.
- **`SALIDA_VENTA`/`SALIDA_BAJA`/`SALIDA_CONSUMO`/`ENTRADA_AJUSTE`/`ENTRADA_DEVOLUCION`**: no hay
  FK estructurada a Cliente en `MovimientoInventario` (solo `cliente_referencia`, texto libre —
  ver `F22_INVENTARIO_BASELINE.md` §1). Se usa `TipoTercero.OTRO` con
  `razon_social=movimiento.cliente_referencia or movimiento.origen_referencia or 'N/A'`. Resolver
  un Cliente real requeriria que `ventas`/`facturas` primero generaran el movimiento con una
  referencia estructurada — fuera de alcance de F22 (ver `F22_INVENTARIO_BASELINE.md` §4).

## 4. Documento origen para Contabilidad (F22.6)

```python
DocumentoOrigen(
    app_label='inventario',
    modelo='MovimientoInventario',
    id=movimiento.id,
    numero=f"MOV-{movimiento.id}",
)
```

**No** se usa el `documento_origen_*` de F21 (que apunta a `RecepcionCompraItem`/
`TrasladoInventario`) como documento origen del asiento — ese campo es la trazabilidad interna de
Inventario (para que Kardex no duplique el `MovimientoInventario`), mientras que el documento
origen de Contabilidad debe ser el registro que Inventario expone al extractor, exactamente el
mismo patron que `ExtractorGastos` (usa `DocumentoSoporte`, no lo que origino el
`DocumentoSoporte`). Idempotencia real: `AsientoContable` tiene
`UniqueConstraint(['empresa','documento_origen_app','documento_origen_modelo','documento_origen_id'],
condition=Q(documento_origen_reversado=False))` — un `MovimientoInventario` nunca puede generar
2 asientos activos.

## 5. Traslados entre sedes — impacto economico = 0 (decision confirmada, no asumida)

Un traslado interno entre 2 `Sede` de la misma `Empresa` no representa una transaccion economica
externa (no hay tercero, no hay cambio de propiedad, no hay ingreso/gasto). Confirmado contra la
logica contable existente: no existe ningun `TipoTransaccion` en `dtos.py` para "traslado interno"
ni ninguna `ReglaContable` seedeada para `TRASLADO_SALIDA`/`TRASLADO_ENTRADA` — el sistema nunca
contemplo contabilizarlos. Implementacion: `ExtractorInventario.extraer_pendientes()` filtra estos
2 tipos fuera del queryset desde el inicio (nunca se construye un DTO para ellos) — mas simple y
mas seguro que construir un DTO con `monto=0` (que `validar_no_vacio()` rechazaria de todas formas
como "Asiento vacio"). Si en el futuro la empresa necesita contabilidad por centro/sede con
movimientos internos entre sedes, es una decision de negocio nueva que requiere su propio
`TipoTransaccion` — no se agrega especulativamente en F22.

## 6. Manejo de `costo_unitario = 0` (riesgo de dato real, ver `F22_INVENTARIO_BASELINE.md` §1)

El extractor NO omite silenciosamente estos movimientos (eso ocultaria informacion real: el
movimiento SI necesita contabilizarse, solo que el dato de costo esta incompleto). En su lugar:
se incluye en `extraer_pendientes()` igual que cualquier otro, y al llegar a
`Contabilizador.contabilizar()` con `monto=0` en ambas lineas, `validar_no_vacio()` lanza
`AsientoNoCuadradoError` — capturado por `contabilizar_pendientes()` (ya existente en
`AbstractExtractor`, sin cambios) y agregado a `resultados['errores']`, aislado del resto del
batch. Es visible en el resultado del comando (`backfill_contabilidad --extractores=inventario`),
no silencioso ni fatal.

## 7. Sede — no se propaga a `AsientoContable`/`MovimientoContable`

Ninguno de los 2 modelos contables tiene campo `sede`/`sede_id`. Decision (F22.20 del prompt
maestro exige documentar, no asumir): **no se agrega**. Razon: agregar `sede_id` a
`AsientoContable`/`MovimientoContable` "solo para resolver F22" esta prohibido explicitamente por
el prompt maestro (§4.5) y no hay ningun requisito de negocio verificado (ReglaContable,
reportes existentes) que lo necesite hoy — la trazabilidad de sede sigue disponible indirectamente
via `MovimientoInventario.sede` -> `documento_origen_id` en el asiento, sin duplicar el dato.

## 8. Costo de venta separado (`INVENTARIO_COSTO_VENTA`) — no usado en F22

El quinto `TipoTransaccion` (`INVENTARIO_COSTO_VENTA`) tiene sus propias reglas seedeadas
(`COSTO_VENTAS`/`INVENTARIO_MERCANCIAS`) pero **no tiene ningun `MovimientoInventario.tipo`
correspondiente** — es un tipo de transaccion mas generico, probablemente pensado para un futuro
proceso de cierre de costos (ej. costeo periodico), no para un movimiento individual de Kardex.
F22 no lo usa: `SALIDA_VENTA` ya cubre el costo de venta por movimiento individual via
`SALIDA_INVENTARIO_VENTA`. Se documenta para que una fase futura no lo redescubra desde cero.
