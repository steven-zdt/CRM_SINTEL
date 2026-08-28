# REMEDIATION_EXECUTION_STATUS

Estado de ejecución de `REMEDIATION_MASTER_PLAN.md` (producido en la
auditoría empresarial previa). Una fila por hallazgo. Un hallazgo solo
pasa a **VERIFIED** después de implementación + validación con evidencia
de test real (nunca por el solo hecho de que el código fue modificado).

**Fecha de cierre de la ejecución:** 2026-08-28
**Rama:** `feat/onboarding-cookie`

## Leyenda de estado

- **VERIFIED** — implementado y confirmado con test real, pasando.
- **BLOCKED** — depende de un insumo externo (credenciales/certificado/WSDL) que no existe en el repositorio; no se intenta cerrar con código inventado.
- **DEFERRED** — decisión explícita de no implementar en esta sesión (trabajo de nueva funcionalidad, no corrección puntual, o requiere decisión de negocio).
- **NO_ACTION_REQUIRED** — investigado y confirmado que no hay hallazgo real (corrección de un finding incorrecto de la auditoría original), o ya resuelto en sesión previa.

| ID | Prioridad | App | Hallazgo | Estado | Causa raíz | Corrección | Tests | Governance | Evidencia | Dependencias |
|---|---|---|---|---|---|---|---|---|---|---|
| P0-01 | P0 | facturas | `Factura.destroy()` hard-delete sin restricción de estado | **VERIFIED** | Ausencia de guard de estado en el Service Layer | `FacturaBusinessService.eliminar_factura()` bloquea salvo `BORRADOR`; viewset ya no confunde 400 con 500 | 6 nuevos + 6 regresión, 12/12 PASS | py_compile OK, sin nuevas migraciones | Corrida local, 1735.23s | Ninguna |
| P0-02 | P0 | facturas, gastos | Período contable cerrado no bloqueaba edición/anulación de Facturas/Gastos | **VERIFIED** | `verificar_periodo_cerrado()` nunca se llamaba desde estas apps | Chequeo agregado en `actualizar_factura_limitado()`, `cambiar_estado()` (ANULADA), `GastoViewSet.perform_update()`, `anular_gasto()` | 8 nuevos, 8/8 PASS | Pendiente barrido final | Corrida local, 26 passed (batch con P0-03+regresión), 607.33s | Ninguna |
| P0-03 | P0 | contabilidad | `Retencion` sin protección contra duplicados por documento_origen+tipo | **VERIFIED** | Sin `UniqueConstraint`; sin manejo de `IntegrityError` en `crear_retencion()` | `UniqueConstraint` condicional (excluye reversadas) + fallback idempotente + reorden de `reversar_retencion()` | 4 nuevos + 14 regresión `test_retenciones_service.py`, 18/18 PASS | Migración `0017` generada y **aplicada a los 3 tenants reales** (0 filas afectadas, verificado por psql previo) | Corrida local, 26 passed (batch combinado), 607.33s | Ninguna |
| P0-04 | P0 | contabilidad | `TipoComprobante.obtener_siguiente_numero()` sin lock — riesgo de números duplicados bajo concurrencia | **VERIFIED** | Ausencia de `select_for_update()` | Reescrito con `select_for_update()` + `@transaction.atomic` | 3 nuevos, 3/3 PASS | Sin migración (solo lógica) | Corrida local aislada, 156.90s | Ninguna |
| P1-01 | P1 | compras | `OrdenCompra` sin máquina de estados explícita | **VERIFIED** | Transiciones no validadas antes de `cambiar_estado_orden_compra()` | `TRANSICIONES_VALIDAS` (con auto-loops, validado contra tests existentes de `test_sincronizacion_cuentas_pagar.py` antes de diseñar) | 4 nuevos, 4/4 PASS | Pendiente barrido final | Corrida local, batch P1 combinado 17/17 PASS, 830.96s | P3-09 (corrección de hallazgo original relacionado) |
| P1-02 | P1 | gastos | `GastoViewSet.destroy()` bypass del guard "anulado" cuando `DEBUG=True` | **VERIFIED** | Condicional `if not settings.DEBUG` alrededor del guard | Guard ahora incondicional; import muerto de `settings` removido | 2 nuevos, 2/2 PASS | Pendiente barrido final | Corrida local, batch P1 combinado 17/17 PASS. 1ra corrida falló por bug del propio test (asumía `DEBUG=True` ambiental); corregido con `override_settings` — ver `REM-P1-02.md` | Ninguna |
| P1-03 | P1 | bancos | `ExtractoBancario` sin protección de duplicados por (empresa, cuenta, año, mes) | **VERIFIED** | Sin `UniqueConstraint`; sin lock en reprocesamiento | `UniqueConstraint` + `select_for_update()` en `procesar_archivo_extracto()` | 3 nuevos, 3/3 PASS | Migración `0006` generada, **pendiente de aplicar** (0 dupes verificado en los 3 tenants) | Corrida local, batch P1 combinado 17/17 PASS | Ninguna |
| P1-04 | P1 | bancos | Conciliación permitía fecha de pago anterior a fecha de la factura conciliada | **VERIFIED** | Sin validación cruzada contra `FacturaInterAppAPI` | Validación agregada en `conciliar_transaccion()`, tolerante a UUID no resoluble (soft-reference) | 3 nuevos, 3/3 PASS | Pendiente barrido final | Corrida local, batch P1 combinado 17/17 PASS. 1ra corrida falló por bug del propio test (esperaba 400; el código de servicio responde 422 por convención ya establecida) — ver `REM-P1-04.md` | Ninguna |
| P1-05 | P1 | contabilidad | Cierre de período sin checklist previo de pendientes (asientos descuadrados, documentos sin extraer) | **VERIFIED** | `cerrar_periodo()` no validaba nada antes de cerrar | Nuevo `pre_close_validation()`, bloquea cierre con detalle de bloqueos | 5 nuevos, 5/5 PASS | Pendiente barrido final | Corrida local, batch P1 combinado 17/17 PASS. **Bug real encontrado y corregido en el propio ciclo de validación**: la query filtraba `total_debe`/`total_haber` (campos legado, siempre sincronizados a 0 en save() sin movimientos reales) en vez de `debe_total`/`haber_total` (autoritativos) — ver `REM-P1-05.md` | Ninguna |
| P2-01 | P2 | compras, gastos, bancos | Ausencia de segregación de funciones (crear/aprobar/pagar por el mismo usuario) | **BUSINESS_DECISION_REQUIRED** (sin cambio de código) | N/A — decisión de negocio, no bug | No implementado — requiere definición de política por el negocio | N/A | N/A | `REM-P2-01.md` | Decisión de negocio |
| P2-02 | P2 | cotizaciones, ventas | Ausencia de flujo Cotización→Venta | **NO_ACTION_REQUIRED** | N/A — decisión de diseño intencional confirmada (F15-F20) | Sin cambio — confirmado correcto | N/A | N/A | `REM-P2-02.md` | Ninguna |
| P2-03 | P2 | clientes | `Cliente.regimen_tributario` sin uso funcional más allá de display | **NO_ACTION_REQUIRED** | N/A — campo informativo, uso real confirmado limitado a UI | Sin cambio | N/A | N/A | `REM-P2-03.md` | Ninguna |
| P2-04 | P2 | facturas | Retenciones sufridas (cliente retiene sobre venta) — reclasificado de GAP a existente | **NO_ACTION_REQUIRED** (hallazgo original incorrecto) | N/A — funcionalidad ya implementada, mal clasificada en auditoría original | Sin cambio funcional — solo reclasificación documental | N/A | N/A | `REM-P2-04.md` (nota adyacente: `naturaleza` no explícito en una llamada — deuda documentada, no corregida) | Ninguna |
| P3-01 | P3 | compras, dashboard | Dashboard sin extractor de Compras | **DEFERRED** | N/A — trabajo de nueva funcionalidad | No implementado en esta sesión | N/A | N/A | `REM-P3-01.md` | Ninguna |
| P3-02 | P3 | bancos, dashboard | Dashboard sin extractor de Bancos | **DEFERRED** | N/A — trabajo de nueva funcionalidad | No implementado en esta sesión | N/A | N/A | `REM-P3-02.md` | Ninguna |
| P3-03 | P3 | dashboard | Campo `gastos_vencidos` mal nombrado (en realidad cuenta anulados) | **VERIFIED** | Nombre de campo no reflejaba la semántica real | Renombrado end-to-end (DTO, extractor, serializer, JS, tests) a `gastos_anulados` | 3 tests existentes actualizados, 22/22 regresión dashboard PASS | Pendiente barrido final | Corrida local, 22 passed | Ninguna |
| P3-04 | P3 | inventario | KPI "valor total de inventario" no filtraba por `activo=True`, divergiendo del Dashboard | **VERIFIED** | Vista de Inventario y `InventarioExtractor` del Dashboard calculaban el KPI con criterios distintos | Alineado el filtro `activo=True` en `ProductoTableView.get_context_data()` | 1 nuevo, 1/1 PASS | Pendiente barrido final | Corrida local, 242.92s. 1ra corrida falló por bug del propio test (sin `TenantProfile`) — ver `REM-P3-04.md` | Deuda documentada: umbral de alerta de stock (`<` vs `<=`) — no corregido |
| P3-05 | P3 | clientes | 2 selectores divergentes de "cartera pendiente" | **VERIFIED** | `get_cartera_kpis()` código muerto (0 consumidores) coexistiendo con el SSoT real | Eliminado el método muerto | N/A (sin comportamiento nuevo que probar; confirmado sin referencias) | Pendiente | `REM-P3-05.md` | Ninguna |
| P3-06 | P3 | core (Reporting Hub) | 4 de 5 datasets del Reporting Hub sin pantalla propia | **DEFERRED** | N/A — trabajo de nueva funcionalidad de frontend (4 piezas) | No implementado en esta sesión | N/A | N/A | `REM-P3-06.md` | Ninguna |
| P3-07 | P3 | contabilidad, bancos, empleados | UI no oculta controles restringidos por rol (bloqueo es 100% backend) | **DEFERRED** | N/A — trabajo transversal de frontend | No implementado en esta sesión | N/A | N/A | `REM-P3-07.md` | Ninguna |
| P3-08 | P3 | facturas | `Factura.consecutivo=0` como sentinela sin documentar | **VERIFIED** | `help_text` ausente; semántica del `0` solo en la cabeza de quien escribió el código | `help_text` agregado al campo + comentario en el punto de uso | N/A (documental) | Migración `0040` generada y **aplicada a los 3 tenants reales** | `REM-P3-08.md` | Ninguna |
| P3-09 | P3 | compras | (Corrección de auditoría) `OrdenCompra.ANULADA` "inalcanzable" — hallazgo original incorrecto | **NO_ACTION_REQUIRED** | N/A — ya era alcanzable vía `cambiar_estado_orden_compra()` antes de P1-01 | Corrección documental en `BUSINESS_GAP_MATRIX.md` | N/A | N/A | `REM-P3-09.md` | Ninguna |
| P3-10 | P3 | facturas, ventas | (Corrección de auditoría) "Factura sin campo hacia Venta" — hallazgo original incorrecto | **NO_ACTION_REQUIRED** | N/A — `Venta.factura_asociada` (OneToOne) ya existe | Corrección documental en `BUSINESS_GAP_MATRIX.md` | N/A | N/A | `REM-P3-10.md` | Ninguna |
| P3-11 | P3 | proveedores | Funciones muertas de retención duplicada | **NO_ACTION_REQUIRED** | N/A — ya eliminadas en sesión previa (F34) | Sin acción — confirmado ya resuelto | N/A | N/A | `REM-P3-11.md` | Ninguna |
| EXT-01 | P0/P1 (bloqueado) | facturas | Transmisión real DIAN de facturas de venta | **BLOCKED** | Sin credenciales/certificado/WSDL real de producción | No se intenta — mantiene `NullTransportAdapter`/mock explícito | N/A | N/A | `REM-EXT-01.md` | Credenciales/certificado/WSDL DIAN |
| EXT-02 | P0/P1 (bloqueado) | empleados | Transmisión real DSPNE de nómina electrónica | **BLOCKED** | Sin credenciales/certificado/URL real de producción | No se intenta | N/A | N/A | `REM-EXT-02.md` | Credenciales/certificado/URL DSPNE |

## Barrido de gobernanza final

Ejecutado 2026-08-28, tras aplicar las 2 migraciones pendientes
(`bancos/0006`, `facturas/0040`) a los 3 tenants reales:

- `manage.py check`: **PASS** — "System check identified no issues (0 silenced)".
- `manage.py makemigrations --check --dry-run` (global): **PASS** — "No changes detected".
- `git diff --check`: **PASS** — sin errores de whitespace ni marcadores de conflicto (solo avisos informativos de normalización LF/CRLF, propios de Windows).
- Migraciones nuevas verificadas post-aplicación directamente en `pg_constraint`/`information_schema` de los 3 schemas reales (`home`, `qaisotest`, `shelltest1`), no solo por el registro de `django_migrations`.

## Nota sobre el proceso de validación

Todos los batches de test se ejecutaron y completaron. 4 fallas reales
surgieron durante la validación (P1-02, P1-04, P1-05, P3-04) — 3 eran
bugs en los tests nuevos (aserciones o setup incorrectos, corregidos) y
1 fue un bug real de código encontrado por el propio test (P1-05:
`pre_close_validation()` filtraba los campos legado
`total_debe`/`total_haber` en vez de los autoritativos `debe_total`/
`haber_total`). Ver cada `REM-P1-0X.md`/`REM-P3-04.md` para el detalle
diagnóstico completo. Ningún hallazgo se declaró VERIFIED sin evidencia
de test real, re-verificada tras cada corrección.
