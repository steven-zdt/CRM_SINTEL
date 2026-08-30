# P0_BASELINE — Fase 0

Baseline de código real para los 4 hallazgos P0 de
`documentacion/auditoria_empresarial/REMEDIATION_MASTER_PLAN.md` (#1-4).
Esta misión ya corrigió y verificó los 4 en una pasada previa (commit
`4dbe80c`, docs `docs/remediation/REM-P0-0{1,2,3,4}.md`); este documento
re-confirma el estado real del código en la rama actual (limpia, en
`4dbe80c`, sin cambios pendientes) antes de la pasada de rigor adicional
que pide esta misión (matrices explícitas, prueba real de concurrencia
para P0-04).

**Fecha:** 2026-08-28
**Commit base:** `4dbe80c`

## P0-01 — `Factura.destroy()`

| Símbolo | Ubicación | Estado real |
|---|---|---|
| `Factura.Estado` | `apps/tenant/facturas/models.py:26-36` | 6 estados: `BORRADOR, ENVIADA, ACEPTADA, RECHAZADA, ERROR_TRANSMISION, ANULADA` |
| `FacturaBusinessService.TRANSICIONES_VALIDAS` | `apps/tenant/facturas/services/business_service.py:73-80` | Matriz de transiciones ya existente (FISCAL-03), `ANULADA` alcanzable desde todo estado no terminal |
| `FacturaBusinessService.eliminar_factura()` | `apps/tenant/facturas/services/business_service.py:100-130` | **Guard activo**: solo `BORRADOR` admite `DELETE` físico; cualquier otro estado levanta `DRFValidationError` |
| `FacturaServiceMixin.service_eliminar()` | `apps/tenant/facturas/services/api_mixins.py` | Llama a `eliminar_factura()` (ya no llama a `FacturaCRUDService.eliminar()` directo) |
| `FacturaViewSet.destroy()` | `apps/tenant/facturas/api/viewsets.py` | Captura `ValidationError` → 400 (antes cualquier excepción caía al genérico → 500) |
| Consumidores de `Factura.delete()`/`.objects...delete()` | grep repo-wide | Ningún otro punto del código llama `Factura.objects.filter(...).delete()` o `.get(...).delete()` fuera del pipeline de `eliminar_factura()` |

**Riesgo residual documentado** (no corregido, fuera de alcance de P0-01
per `REM-P0-01.md`): anular una factura `ACEPTADA` no reversa
automáticamente el `AsientoContable`/`MovimientoInventario` ya extraído —
la anulación cambia el estado de la `Factura`, pero el asiento/movimiento
generado antes de la anulación permanece tal cual (mismo patrón de
"reversa manual" que el resto del sistema hoy, no un gap introducido por
esta corrección).

## P0-02 — `PeriodoContable` cerrado

| Símbolo | Ubicación | Estado real |
|---|---|---|
| `verificar_periodo_cerrado()` | `apps/tenant/contabilidad/services/selectors.py` | Función de solo lectura ya existente, ahora invocada desde 4 puntos reales (antes solo desde `AsientoContable`) |
| `FacturaBusinessService.actualizar_factura_limitado()` | `apps/tenant/facturas/services/business_service.py` | Valida `verificar_periodo_cerrado(factura.fecha_emision, empresa_id)` antes de aplicar PATCH |
| `FacturaViewSet.cambiar_estado()` | `apps/tenant/facturas/api/viewsets.py` | Valida el período solo cuando `nuevo_estado == ANULADA` |
| `GastoBusinessService.anular_gasto()` | `apps/tenant/gastos/services/business_service.py` | Valida período antes de anular |
| `GastoViewSet.perform_update()` | `apps/tenant/gastos/api/viewsets.py` | Nuevo override — valida tanto la fecha actual del documento como la nueva fecha (si cambia) |

## P0-03 — `Retencion` duplicados

| Símbolo | Ubicación | Estado real |
|---|---|---|
| `Retencion.Meta.constraints` | `apps/tenant/contabilidad/models.py` | `UniqueConstraint(fields=[empresa, documento_origen_app, documento_origen_modelo, documento_origen_id, tipo], condition=Q(reversada=False) & ~Q(documento_origen_id=0))` — migración `0017`, **aplicada a los 3 tenants reales** |
| `RetencionesService.crear_retencion()` | `apps/tenant/contabilidad/services/retenciones_service.py` | Captura `IntegrityError` del constraint → retorna la fila activa existente (idempotente) |
| `RetencionesService.reversar_retencion()` | `apps/tenant/contabilidad/services/retenciones_service.py` | `@transaction.atomic`; marca `reversada=True` en el original ANTES de crear la fila de reversa (evita colisión con el constraint en el caso "in place") |

## P0-04 — `TipoComprobante.obtener_siguiente_numero()`

| Símbolo | Ubicación | Estado real |
|---|---|---|
| `TipoComprobante.obtener_siguiente_numero()` | `apps/tenant/contabilidad/models.py` | Reescrito: `select_for_update()` sobre la propia fila dentro de `transaction.atomic()`, antes de leer/incrementar/guardar `consecutivo_actual` |
| Tests previos | `apps/tenant/contabilidad/tests/test_remediation_p0_04_numeracion_comprobante.py` | 3 tests: secuencia sin saltos en 10 llamadas consecutivas (secuenciales, mismo proceso/conexión), persistencia en BD, verificación de código fuente. **Admitido explícitamente como gap**: sin prueba de concurrencia real multi-conexión — exactamente lo que esta misión pide cerrar (ver `P0_04_NUMBERING.md`) |

## Consumidores cross-app de estos 4 símbolos (confirmado por grep, sin duplicar owner)

- `Retencion`/numeración: consumidos por lectura desde `facturas`, `gastos`,
  `compras`, `bancos` (vía `RetencionesService`, nunca ORM directo — bridge ya
  sancionado).
- `verificar_periodo_cerrado()`: consumido por `facturas`, `gastos` (P0-02) y
  por `contabilidad` misma (`AsientoContable`, `cerrar_periodo()`/P1-05).
- `Factura`: referenciada (soft-reference por UUID, nunca FK directa cross-app)
  desde `bancos` (conciliación), `contabilidad` (extractor + retenciones),
  `inventario` (movimientos), `clientes` (cartera), `ventas` (`factura_asociada`).

No se modifica código en esta fase — solo confirmación de baseline.
