# P0_CROSS_APP_VALIDATION

Validación de integridad post-P0 per §13 del programa de remediación:
confirmar que los 4 fixes P0-01..P0-04 **no rompieron contratos
existentes** en la cadena `Facturas → Ventas → Inventario → Impuestos →
Bancos → Contabilidad`. No se crearon integraciones nuevas — solo
verificación.

**Fecha:** 2026-08-30

## Método

Para cada eslabón de la cadena, se identifica el contrato real (función/
endpoint que otras apps consumen) y se confirma que ninguno de los 4
fixes P0 lo modificó, o si lo hizo, que la regresión existente lo sigue
cubriendo.

## FACTURAS (P0-01, P0-02)

**Contrato expuesto:** `FacturaInterAppAPI` (soft-reference read-only,
patrón ya sancionado), `Factura.estado`, `TRANSICIONES_VALIDAS`.

- P0-01 (`eliminar_factura()`) solo interviene en el `DELETE` físico —
  no toca `cambiar_estado()`, `TRANSICIONES_VALIDAS`, ni ningún campo
  leído por `FacturaInterAppAPI`. **Sin impacto en consumidores.**
- P0-02 agrega una validación PREVIA (período cerrado) a
  `actualizar_factura_limitado()` y a la rama `ANULADA` de
  `cambiar_estado()` — no cambia la forma en que otras apps leen
  `Factura`, solo agrega un caso de rechazo (400) que antes no existía.
  Confirmado: `test_scope_facturas_f11.py` (control de acceso por sede,
  6 tests preexistentes, dominio distinto a período) sigue en 6/6 PASS
  sin modificación — no hay colisión de lógica.

## VENTAS

**Contrato expuesto:** `Venta.factura_asociada` (OneToOne hacia
`Factura`), disparador de `SALIDA_VENTA` en Kardex vía
`VentaBusinessService._generar_salida_inventario()`.

- Ninguno de los 4 fixes P0 toca `ventas/`. `Venta.factura_asociada`
  sigue apuntando a la misma `Factura` (P0-01 no permite que esa fila
  desaparezca vía `DELETE` salvo en `BORRADOR`, que nunca tiene una
  `Venta` asociada en el flujo real — confirmado por el pipeline:
  `Venta` solo se crea sobre una `Factura` ya persistida con flujo
  completo). **Sin impacto.**

## INVENTARIO

**Contrato expuesto:** `MovimientoInventario` con
`documento_origen_app='facturas'`, `documento_origen_modelo='ItemFactura'`
(o `'ItemNotaCredito'` para devoluciones).

- P0-01: anular una factura `ACEPTADA` **no revierte** automáticamente
  el `MovimientoInventario` ya generado — comportamiento documentado
  explícitamente como deuda pendiente en `P0_01_FACTURA_DELETE.md`, no
  como regresión (nunca existió reversa automática antes de este fix
  tampoco). **Sin cambio de comportamiento respecto al estado anterior.**
- P0-04 (numeración de comprobantes contables) no tiene ninguna relación
  con `MovimientoInventario` — dominios distintos (`TipoComprobante` es
  exclusivamente de `contabilidad`). **Sin impacto.**

## IMPUESTOS / RETENCIONES (P0-03)

**Contrato expuesto:** `RetencionesService` (bridge cross-app ya
sancionado, consumido por `facturas`, `gastos`, `compras`, `bancos` —
nunca ORM directo).

- El nuevo `UniqueConstraint` + idempotencia en `crear_retencion()` es
  **transparente para los consumidores**: la firma de la función no
  cambió, el contrato de retorno (una instancia `Retencion`) tampoco.
  Un consumidor que llame `crear_retencion()` dos veces con los mismos
  datos ahora recibe la MISMA fila en vez de un `IntegrityError` no
  controlado — es una mejora de robustez del contrato, no una ruptura.
- Confirmado por regresión: los 14 tests preexistentes de
  `test_retenciones_service.py` (que ejercitan exactamente el patrón de
  consumo cross-app: crear, listar, totalizar, reversar) siguen en
  14/14 PASS sin modificación.

## BANCOS

**Contrato expuesto:** `TransaccionBancaria.factura_uuid`/`proveedor_uuid`
(soft-reference), conciliación vía `FacturaInterAppAPI.get_by_id()`.

- Ninguno de los 4 fixes P0 toca `bancos/`. La validación de fecha
  pago-vs-documento (P1-04, ya VERIFIED en la pasada anterior) es un
  hallazgo P1 distinto, no P0. **Sin impacto de los fixes P0 sobre este
  eslabón.**

## CONTABILIDAD (P0-02, P0-03, P0-04)

**Contrato expuesto:** `verificar_periodo_cerrado()` (lectura),
`RetencionesService` (lectura/escritura vía servicio),
`TipoComprobante.obtener_siguiente_numero()` (usado por
`Contabilizador` y por los 4 puntos de numeración ya migrados a
`select_for_update()` en sesiones previas: cotizaciones, compras,
ventas, empleados).

- P0-02: `verificar_periodo_cerrado()` en sí **no fue modificada** — se
  agregaron NUEVOS llamadores (`facturas`, `gastos`), no se tocó su
  firma ni su lógica interna. **Sin impacto en el consumidor original**
  (`AsientoContable`, dentro de la propia app `contabilidad`).
- P0-03: ver arriba (Impuestos).
- P0-04: `obtener_siguiente_numero()` cambió su implementación interna
  (agregó `select_for_update()`) pero **no su firma ni su valor de
  retorno** (`f"{prefijo}{numero}"`, formato sin cambios) — verificado
  por los 3 tests secuenciales preexistentes (formato del número sin
  cambios) + los 2 tests de concurrencia real (mismo formato bajo carga
  concurrente). **Sin impacto en `Contabilizador` ni en ningún otro
  consumidor.**

## Conclusión

**Ningún contrato cross-app fue roto.** Los 4 fixes P0 son, por diseño,
adiciones de guardas (rechazos que antes no existían) o cambios de
implementación interna sin cambio de firma/contrato — consistente con
la "corrección mínima" exigida por el programa. No se detectó
dependencia circular, duplicación de lógica entre apps, ni
inconsistencia introducida. Confirmado con evidencia de regresión real
(no solo inspección de código): 43/43 tests dirigidos, incluyendo toda
la regresión preexistente relevante de cada eslabón tocado, PASS.
