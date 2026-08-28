# Matriz de Controles Internos — SINTEL ERP

**Fecha:** 2026-08-27. Evidencia real de código (archivo:línea), verificada por
agente dedicado en esta sesión — no una matriz de roles nueva inventada.

Clasificación de cada control: **PREVENTIVO** (impide la acción indebida antes
de que ocurra) / **DETECTIVO** (permite detectarla después) / **CORRECTIVO**
(permite revertirla).

---

## 1. Segregación de funciones por flujo transaccional

| Flujo | Segregación de rol real | Evidencia | Clasificación |
|---|---|---|---|
| **Compras** | **NO existe** — `OrdenCompraViewSet.get_permissions()` retorna los mismos permisos (`IsTenantMember`, `IsTenantAdminOrReadOnly`, `HasOrganizationalScope`) para crear, aprobar (`cambiar-estado`) y confirmar recepción. Un mismo ADMIN puede ejecutar todo el ciclo compra→recepción→pago | `apps/tenant/compras/api/viewsets.py:73-78,180,368` | Ausente |
| **Ventas** | No aplica (no hay paso de aprobación intermedio por diseño — factura se genera en la misma transacción que la venta) | `apps/tenant/ventas/services/business_service.py:645-654` | N/A por diseño |
| **Gastos** | **NO existe ningún estado de aprobación** — `DocumentoSoporte` no tiene workflow de aprobación antes de pago, solo `anulado` (booleano post-hoc). Decisión explícita del propio código: *"v2.62: FLEXIBILIDAD OPERATIVA — Reglas de Inmutabilidad deshabilitadas"* | `apps/tenant/gastos/models.py:4-9,112` | Ausente (decisión documentada, no un bug oculto) |
| **Nómina** | **Único control de segregación real y verificado del sistema.** `PeriodoNominaViewSet._ROLES_POR_ACCION`: `preliquidar`/`create`/`enviar_a_revision` → `['ADMIN','OPERADOR']`; `aprobar`/`marcar_pagado`/`cerrar`/`anular` → `['ADMIN']` exclusivamente, aplicado vía `HasTenantRole()`, backend siempre valida (no solo UI) | `apps/tenant/empleados/api/viewsets.py:2110-2135`, comentario explícito en `business_service.py:648-651` | **PREVENTIVO real** — con matiz: no exige que preliquidar/aprobar/pagar sean 3 personas distintas, solo que OPERADOR nunca pueda auto-aprobar |
| **Bancos** | **NO existe** — `permission_classes = [IsTenantMember]` (sin rol diferenciado) para conciliar. Ni siquiera hay trazabilidad de QUIÉN concilió (`TransaccionBancaria` no tiene campo `usuario_concilia`) | `apps/tenant/bancos/api/viewsets.py:275,292-312` | Ausente — ni preventivo ni detectivo |

**Conclusión de esta sección:** de 5 flujos transaccionales auditados, solo 1
(Nómina) tiene segregación de rol real y forzada por backend. Los otros 4
dependen enteramente de que el ADMIN del tenant actúe con disciplina personal
— el sistema no se lo impide ni lo registra.

## 2. Trazabilidad (control DETECTIVO)

| Área | Estado |
|---|---|
| Movimientos de Kardex | **Trazabilidad completa** — `documento_origen_app/modelo/id`, `UniqueConstraint` de idempotencia, timeline unificado (`get_movimientos_timeline()`) |
| Asientos contables | **Trazabilidad completa** — `documento_origen_*` + `documento_origen_reversado` |
| Anulación de Gasto | **Trazabilidad completa** — `motivo_anulacion`/`usuario_anulacion`/`fecha_anulacion` capturados |
| Conciliación bancaria | **Sin trazabilidad de usuario** — ver §1, ningún campo registra quién concilió una transacción |
| Eliminación de Factura | **Sin trazabilidad — ver §3, es DELETE físico** |

## 3. Reversa/anulación vs. hard delete — hallazgo más severo de esta matriz

| Documento | Mecanismo real | Evidencia | Severidad |
|---|---|---|---|
| **Factura** | **CRÍTICO — DELETE físico directo, sin bloqueo, sin reversa.** El propio código documenta la decisión: *"Eliminación directa de facturas (sin restricciones de inmutabilidad)... incluso si tiene notas de crédito asociadas... No hay validaciones que bloqueen la eliminación por vínculos contables"* (v2.95). Borra Factura + NotaCredito + Anexos + ItemFactura en CASCADE, **sin generar ningún movimiento compensatorio** en `MovimientoInventario` ni en `AsientoContable` ya generados — quedan huérfanos referenciando un `documento_origen_id` inexistente. Para una factura electrónica con CUFE ya aceptado por la DIAN, esto es además un problema de cumplimiento (un documento electrónico aceptado no se "borra", se corrige con NC/ND) | `apps/tenant/facturas/api/viewsets.py:532-596`, `services/crud_service.py:68-89` | **CRITICAL** |
| **Venta** | Reversa real y bien gobernada — `anular_venta()` solo permite anular en `BORRADOR`; una vez `FACTURADA_DIAN`, exige Nota Crédito | `apps/tenant/ventas/services/crud_service.py:135-141` | Correcto, sin hallazgo |
| **OrdenCompra** | **`cambiar_estado()` no valida la máquina de estados** — solo verifica que el string de destino exista en las choices, permite saltos arbitrarios (ej. `RECIBIDA → BORRADOR`). Anulación posterior a "aprobada" **no reversa la CxP ya generada** — reconocido explícitamente en el propio código como fuera de alcance | `apps/tenant/compras/services/crud_service.py:245-261`, `business_service.py:360-380` | **HIGH** |
| **RecepcionCompra** | Correcto — `anular_recepcion()` bloquea anulación si ya está `CONFIRMADA` (evita huérfanos de Kardex) | `business_service.py:615-630` | Correcto, sin hallazgo |
| **Gasto** | Reversa real (`anular_documento()`, marca `anulado=True` con motivo/usuario/fecha, no delete) — **pero el `destroy()` del ViewSet se salta esa protección si `settings.DEBUG=True`** | `apps/tenant/gastos/services/crud_service.py:117-127`, `api/viewsets.py:124-134` | **MEDIUM** — mismo patrón de bypass-en-DEBUG que ya se corrigió en Kardex de Inventario en esta misma sesión (commit `399f1c8`) |
| **Asiento Contable** | Correcto — `reversar_asiento()` crea un asiento inverso real (`documento_origen_reversado=True`, montos invertidos), valida período abierto, nunca hace DELETE | `apps/tenant/contabilidad/integracion/contabilizador.py:167-214` | Correcto, sin hallazgo — es el patrón de referencia que Factura debería seguir |

## 4. Cierre de período contable

`PeriodoContable` existe con estados abierto/cerrado; `reversar_asiento()`
valida explícitamente que el período esté abierto antes de reversar (línea
185 de `contabilizador.py`). El mecanismo de apertura/cierre en sí (quién
puede cerrar, si exige pendientes=0) no fue verificado campo por campo en
esta pasada — consistente con el deferred ya registrado en
`APP_contabilidad_NORMATIVE_MATRIX.md`.

## Resumen de clasificación preventivo/detectivo/correctivo

| Control | Tipo | Estado |
|---|---|---|
| Segregación de rol en Nómina | PREVENTIVO | Implementado |
| Bloqueo de anulación de Venta facturada | PREVENTIVO | Implementado |
| Bloqueo de anulación de Recepción confirmada | PREVENTIVO | Implementado |
| Reversa de Asiento Contable (asiento espejo, no delete) | CORRECTIVO | Implementado, patrón de referencia |
| Anulación de Gasto con trazabilidad de usuario | DETECTIVO + CORRECTIVO | Implementado, con bypass en DEBUG (gap MEDIUM) |
| Bloqueo de eliminación de Factura con vínculos | PREVENTIVO | **Ausente — gap CRITICAL** |
| Validación de transición de estado en OrdenCompra | PREVENTIVO | **Ausente — gap HIGH** |
| Reversa de CxP al anular OrdenCompra aprobada | CORRECTIVO | **Ausente — gap HIGH** |
| Trazabilidad de usuario en conciliación bancaria | DETECTIVO | **Ausente** |
| Segregación de rol en Compras/Gastos/Bancos | PREVENTIVO | **Ausente en las 3** |
