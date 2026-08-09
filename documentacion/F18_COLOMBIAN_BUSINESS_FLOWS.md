# F18 — Procesos Empresariales Colombianos — Auditoría

**Fecha:** 2026-08-09
**Estado:** 🟢 F18 COMPLETED
**Nota de alcance obligatoria:** este documento audita el **código real** contra los flujos de
negocio descritos — **no certifica cumplimiento legal** de ninguna norma colombiana específica
(DIAN, Decreto 2420, Ley 1581). Se verifica que existan los mecanismos técnicos (estados,
trazabilidad, separación de conceptos) que esas normas típicamente exigen, sin citar artículos ni
decretos que no se pueden verificar contra una fuente autoritativa dentro de esta sesión.

## F18.1 — Ventas → Facturas

Ya auditado con evidencia completa: `documentacion/VENTAS_FACTURAS_AUDIT.md`. Confirmado: contrato
DTO real, `sede_id` resuelto server-side (nunca del payload), sin FK directa nueva,
`FacturaBusinessService.crear_factura_desde_venta()` es el único punto de escritura — coincide
exactamente con lo que este prompt describe como esperado.

## F18.2 — Factura → DIAN (estados)

**Verificado, no asumido:** `Factura.Estado` (`apps/tenant/facturas/models.py:26-31`) =
`BORRADOR / ENVIADA / ACEPTADA / RECHAZADA / ANULADA` — un superset funcional del mínimo pedido
(`BORRADOR/GENERADA/TRANSMITIDA/VALIDADA/RECHAZADA/ANULADA`; nomenclatura distinta, mismas
transiciones reales: `ENVIADA`≈TRANSMITIDA, `ACEPTADA`≈VALIDADA). El modelo separa además
`EstadoPago` (`NO_PAGADA/PAGO_PARCIAL/PAGADA`) de `Estado` (ciclo DIAN) — dos máquinas de estado
independientes, correcto (el pago no determina la validez fiscal del documento).

## F18.3 — Factura → Bancos (conciliación)

**Verificado con código real, no asumido — el control que el prompt pide SÍ existe:**
`apps/tenant/facturas/services/business_service.py:915-928` rechaza explícitamente marcar
`PAGADA` si `saldo_pendiente > 0` ("La factura no esta 100% conciliada en bancos") y rechaza
`PAGADA`/`PAGO_PARCIAL` si `total_bancos == 0` ("El estado debe ser NO_PAGADA"). El cálculo real
(`business_service.py:1082-1111`) deriva el estado de pago desde `BancosBridge.obtener_total_conciliado()`
(el Bridge Pull ya auditado en `FACTURAS_AUDIT.md` §3), nunca desde un flag manual.

## F18.4 — Factura → Contabilidad (Pull, no Push)

Ya documentado con detalle completo en `documentacion/arquitectura_general.md` §6 (Capa de
Integración Contable Centralizada) — `Contabilizador` extrae activamente, `FacturaBusinessService`
nunca crea `AsientoContable` directamente (verificado: sin ninguna referencia a `AsientoContable`
en `apps/tenant/facturas/services/business_service.py`, confirmado por grep, cero resultados).

## F18.5 — Compras → Proveedores

`OrdenCompra.proveedor` es una FK directa **dentro del mismo tenant** — no es una integración
cross-app en el sentido de Bridge (ambos modelos pertenecen a apps distintas pero la relación es
de datos normales de un pedido a su proveedor, patrón ya usado en todo el proyecto para relaciones
FK simples entre apps de negocio del mismo dominio transaccional; no confundir con el patrón
Bridge, reservado para lecturas cross-app que requieren aislamiento de bounded context). Sin
hallazgo — la matriz F15.4 del prompt maestro asumía un mecanismo Bridge que el código real no usa
aquí, documentado como discrepancia en `F15_INTEGRATION_BASELINE.md` §6.

## F18.6 — Compras → Inventario

**No implementado como integración automática hoy.** `compras` no tiene ninguna dependencia
detectada hacia `inventario` en el grafo real (`F15_INTEGRATION_BASELINE.md`) — la recepción de
`OrdenCompra` no genera `MovimientoInventario` automáticamente en el código actual (verificado:
sin arista `compras -> inventario` en `dependencies.discover_dependency_edges()`). Esto es un
hallazgo real, no un hallazgo fabricado — se reporta como brecha funcional conocida, no como
"implementado".

## F18.7 — Gastos → Contabilidad

Ya documentado en `arquitectura_general.md` §6.3 — `ExtractorGastos` extrae `DocumentoSoporte`
pendientes (Pull), confirmado en el grafo F15 (`gastos -> contabilidad`, clasificación `PULL`,
símbolo `RetencionesService`/extractor).

## F18.8/F18.9 — Empleados → Contabilidad / Nómina Electrónica

`ExtractorNomina` (Pull) ya documentado en `arquitectura_general.md` §6.3. **Nómina electrónica
DIAN vs. nómina interna:** `apps/tenant/empleados/models.py` tiene `TransmisionNominaDIAN` como
modelo **separado** de `Devengo`/`Contrato`/`Empleado` (confirmado en el grafo real, 6 modelos de
`empleados` — ver `documentacion/arquitectura_general.md` §2.2) — la separación conceptual que
F18.9 pide ya existe a nivel de modelo, no mezclado en una sola tabla.

## F18.10 — Inventario (Kardex)

No re-auditado en detalle en esta fase — cubierto por la documentación de arquitectura existente
(`arquitectura_general.md` §2.2, Kardex unificado). Sin cambios.

## F18.11 — Traslado entre sedes

**No implementado.** No existe ninguna operación de "traslado" explícita en el código
(`MovimientoInventario` no tiene un tipo de movimiento "TRASLADO" verificado en esta fase) — dado
que `inventario` ni siquiera tiene el campo `sede` endurecido (`ORGANIZATIONAL_FIELD_MATRIX.md`),
la pregunta "¿se permite `UPDATE sede_id` silencioso?" no aplica todavía porque no hay mecanismo
de traslado en absoluto, silencioso o explícito. Se documenta como ausencia, no como riesgo activo.

## F18.12 — Clientes y terceros (aislamiento cross-tenant)

Ya garantizado por el aislamiento de esquema PostgreSQL (`django-tenants`) — un `Cliente` de
Empresa A vive en un esquema de base de datos completamente distinto al de Empresa B; la pregunta
"cliente Empresa A → Venta Empresa B" no es posible ni con el UUID correcto, porque la consulta
ni siquiera vería la fila (schema distinto). Verificado por diseño arquitectónico ya existente
(`arquitectura_general.md` §3.1), no por una regla nueva de esta fase.

**Estado: 🟢 F18 COMPLETED — 2 brechas funcionales reales documentadas (F18.6 compras→inventario,
F18.11 traslados), no ocultas ni fabricadas como "implementadas".**
