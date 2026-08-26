# CONT-19 — Baseline real del ciclo contable (FASE 0)

**Fecha:** 2026-08-26
**Alcance:** Baseline previo a la validacion end-to-end de CONT-19. No reemplaza `AUDITORIA_COMPLETA_CONTABILIDAD.md` (fuente canonica del app) — lo referencia y se limita a lo necesario para ejecutar CONT-19.

---

## 1. Flujo real confirmado (codigo, no intencion)

```
APP ORIGEN (facturas/gastos/empleados/inventario)
    v
EXTRACTOR (extraer_pendientes / get_documentos_enriquecidos)
    v
TransaccionEconomica DTO (integracion/dtos.py)
    v
Contabilizador.contabilizar() -- integracion/contabilizador.py
    v  (resuelve cuenta via ResolverCuentas + ReglaContable)
AsientoContable (estado=BORRADOR) + MovimientoContable (cuenta_codigo)
```

Confirmado en `integracion/contabilizador.py::_construir_asiento()`: cada `MovimientoContable` se crea con `cuenta_codigo` (string PUC), **nunca** con el FK legacy `cuenta`. Este es el hecho arquitectonico mas importante de todo el ciclo — determina qué lectura de `cuenta`/`cuenta_codigo` es correcta en cualquier lugar del código (extractores, selectors, serializers).

`AsientoContable.estado`: `BORRADOR` (default, todo lo que crea `Contabilizador`) -> `APROBADO` (vía `aprobar_asiento`, valida cuadratura) -> `CERRADO` (vía cierre de periodo). Los reportes (`balance_prueba_selector`, `estado_resultados_selector`) filtran deliberadamente `estado='APROBADO'` — diseño correcto, no bug.

## 2. Apps origen — clasificacion (FASE 1)

| Origen | Estado | Evidencia |
|---|---|---|
| Facturas | **OPERATIVO** | `ExtractorFacturas` real; verificado en vivo esta sesion (Factura 1300962, home tenant, sesion previa) |
| Gastos | **OPERATIVO** | `ExtractorGastos` real; verificado en vivo esta sesion (DocumentoSoporte GA-1, home tenant, CONT-19) |
| Nomina (empleados) | **OPERATIVO** | `ExtractorNomina` real; verificado en vivo esta sesion (Devengo 2026-08, home tenant, CONT-19) |
| Inventario | **OPERATIVO** | `ExtractorInventario` real; verificado con test real end-to-end (test_f27, compra completa hasta asiento) |
| Compras | **NO_APLICA (directo)** | Cero referencias a `documento_origen_app='compras'` en contabilidad; cero `AsientoContable`/`MovimientoContable` creado en `apps/tenant/compras/`. Compras alimenta Contabilidad **solo indirectamente**: `RecepcionCompra` -> `MovimientoInventario(ENTRADA_COMPRA)` -> `ExtractorInventario`. Un solo camino, sin doble contabilizacion. |
| Ventas | **NO_APLICA (directo)** | Mismo patron: cero `AsientoContable`/`MovimientoContable` en `apps/tenant/ventas/`; comentario explicito en `ventas/services/business_service.py:678` confirmando que Contabilidad se resuelve solo vía `ExtractorInventario`. Ventas alimenta Contabilidad por DOS caminos distintos y complementarios (no duplicados): ingreso/CxC vía `Venta -> Factura -> ExtractorFacturas`, y costo/inventario vía `Venta -> MovimientoInventario(SALIDA_VENTA) -> ExtractorInventario`. |
| Bancos | **NO_APLICA** | `apps/tenant/bancos/` existe como app independiente (conciliacion), cero referencias a `AsientoContable`/`MovimientoContable`/`documento_origen_app='bancos'`. Contabilidad no posee ni duplica movimientos bancarios. |

**Riesgo de doble contabilizacion: NINGUNO.** Reforzado ademas por constraint unico en BD sobre `(empresa, documento_origen_app, documento_origen_modelo, documento_origen_id)` (`contabilidad/models.py`, migracion `0016`).

## 3. Bug critico encontrado y corregido esta sesion (antes de CONT-19)

`Contabilizador` solo llena `cuenta_codigo`, nunca el FK `cuenta` — pero 3 extractores (facturas/gastos/nomina) y 2 selectores de reportes (`balance_prueba_selector`, `estado_resultados_selector`) leian/filtraban solo por `cuenta`/`cuenta__*`. Efecto real: Balance de Prueba y Estado de Resultados vacios, Libro Diario con `SIN_CUENTA`, para CUALQUIER tenant usando la integracion real. Corregido y verificado con datos reales (ver `AUDITORIA_COMPLETA_CONTABILIDAD.md`, nota 2026-08-25, y `tests/test_f27_cuenta_codigo_reportes_bugfix.py`).

## 4. Deuda tecnica activa (AUD-CONT-005 a 011) — clasificacion para CONT-19

| ID | Severidad | Decision CONT-19 | Razon |
|---|---|---|---|
| AUD-CONT-005 | Baja | DIFERIR | Archivo legacy no expuesto, cero impacto funcional |
| AUD-CONT-006 | Baja | DIFERIR | Scripts no productivos, cero impacto funcional |
| AUD-CONT-007 | Media | **RESUELTO** (corregido en doc, verificado 2026-08-26) | El doc estaba desactualizado — `tasks.py` YA tiene `max_retries=3` + DLQ real (`registrar_failed_task`/`FailedTenantTask`). Verificado leyendo el codigo actual. |
| AUD-CONT-009 | Baja | DIFERIR | Requiere migracion de modelo (agregar UUID a `ConfiguracionRetenciones`) — fuera del alcance minimo de CONT-19 |
| AUD-CONT-010 | Baja | DIFERIR | Ya aceptado como riesgo menor en auditoria previa (endpoint read-only) |
| AUD-CONT-011 | Info | DIFERIR | Doc explicito: "agregar test cuando el usuario lo pida" — no solicitado |

## 5. Documentos de referencia ya leidos (no releidos completos en CONT-19, ya cubiertos por auditoria previa de esta misma sesion)

`models.py`, `services/selectors.py`, `services/crud_service.py`, `services/business_service.py`, `services/retenciones_service.py` (parcial), `integracion/dtos.py`, `integracion/contabilizador.py`, `integracion/resolver.py`, `integracion/extractores/*.py`, `api/viewsets.py`, `api/serializers.py`, `tasks.py`, `.agent/docs/contabilidad_flow_map.md`, `.agent/docs/contabilidad_business_logic.md`.
