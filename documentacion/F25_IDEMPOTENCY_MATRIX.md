# F25 — Matriz de Idempotencia

**Fecha:** 2026-08-10

| Caso | Mecanismo real | Operacion critica | Resultado verificado |
|---|---|---|---|
| POST duplicado / retry HTTP | `UniqueConstraint uniq_movimiento_documento_origen_tipo` (`MovimientoInventario`, F21) | `KardexService.registrar_movimiento()` | 1 movimiento (test real F21: `test_reintentar_generar_salida_no_duplica_movimiento`, F23) |
| POST duplicado / retry HTTP | Idempotencia por CUFE (`guardar_desde_dto`, chequeo antes de cualquier escritura) | Persistencia de Factura/NotaCredito | 1 documento (codigo real, ver F25-FP-013) |
| POST duplicado / retry HTTP | `UniqueConstraint uniq_asiento_documento_origen_no_reversado` (`AsientoContable`, F22) + chequeo previo `_validar_no_existe()` | `Contabilizador.contabilizar()` | 1 asiento (test real F22/F24: `test_f24_idempotencia_contable_doble_corrida`) |
| Doble click (misma venta, 2 requests) | Mismo `UniqueConstraint` de `MovimientoInventario`, mas `select_for_update()` en `KardexService` para la carrera real entre 2 transacciones concurrentes | `procesar_y_facturar_venta()` -> `_generar_salida_inventario()` | 1 `SALIDA_VENTA` por `ItemVenta` (test real F23) |
| Doble click (misma recepcion) | `select_for_update()` sobre `RecepcionCompra` (serializa) + `UniqueConstraint` de `MovimientoInventario` (respaldo ante carrera real) | `confirmar_recepcion()` | 1 confirmacion, no-op idempotente en el segundo intento (test real F21) |
| Celery retry (`procesar_factura_xml_task`) | Idempotencia por CUFE (heredada de `guardar_desde_dto`) | Reintento tras fallo transitorio | 1 Factura (ver F25-002 en `F25_FINDINGS.md`) |
| Celery retry (`ejecutar_integracion_contable_task`) | `UniqueConstraint` de `AsientoContable` + aislamiento por documento en `contabilizar_pendientes()` | Reintento de la tarea completa tras fallo parcial | Documentos ya contabilizados se saltan (`omitidos`), pendientes reales se procesan, sin duplicados (ver F25-002) |
| Worker restart / timeout | Mismo mecanismo que retry (los `UniqueConstraint` son a nivel de base de datos, sobreviven a un restart del proceso) | Cualquiera de los anteriores | Sin duplicacion (garantia de BD, no de aplicacion) |
| Reprocesamiento manual (backfill) | `contabilizar_pendientes()` excluye documentos ya contabilizados via `.exclude(id__in=ya_contabilizados)` antes de intentar nada | `ExtractorInventario.extraer_pendientes()` | 0 duplicados (verificado F22/F24) |
| Concurrencia real (2 transacciones simultaneas sobre el mismo documento) | `UniqueConstraint` de BD como respaldo -- el chequeo previo (`.exists()`/idempotency check) no es atomico frente a 2 transacciones que lo pasan antes de hacer commit, pero la constraint de BD rechaza el segundo INSERT, traducido a `AsientoYaExisteError`/movimiento existente devuelto | `Contabilizador.contabilizar()`, `KardexService.registrar_movimiento()` | 1 resultado empresarial (garantia de BD, documentado explicitamente en el codigo, ver `contabilizador.py` lineas 125-140) |

## Conclusion

Ningun caso de idempotencia requirio un mecanismo nuevo. Todos se resuelven con la
combinacion ya establecida de `UniqueConstraint` (respaldo de ultima linea ante
condiciones de carrera reales) + chequeo previo en aplicacion (camino rapido, evita
el roundtrip de error de BD en el caso normal de reintento secuencial) +
`select_for_update()` donde la operacion requiere serializar lecturas-antes-de-escribir
(stock, consecutivos). No se crea un framework de idempotencia nuevo (regla F25 §24).
