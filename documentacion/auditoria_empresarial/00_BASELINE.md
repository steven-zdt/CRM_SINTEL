# FASE 0 — Baseline Empresarial — Auditoría Integral SINTEL

**Fecha:** 2026-08-27. Rama `feat/onboarding-cookie`.

## Fuentes de verdad usadas, en orden de autoridad (regla de la misión)

1. Código real (`apps/tenant/**`) — leído y verificado directamente donde se cita.
2. Migraciones/BD — verificadas puntualmente (ej. `UniqueConstraint` de Cliente/Proveedor).
3. Contratos API/servicios reales — verificados vía lectura de `business_service.py`/`viewsets.py`.
4. Tests existentes — citados donde confirman un flujo (ej. `test_devolucion_nota_credito.py`).
5. Documentación SSoT actual por app — los 9 `documentacion/audits/apps/APP_*_NORMATIVE_MATRIX.md`
   y 2 misiones de auditoría completas previas (`APP_AUDIT_MASTER_FINAL.md` 2026-08-21,
   `F34_MASTER_FINAL.md` 2026-08-21), usadas como base verificada, no re-derivadas desde cero.
6. Documentación histórica (`F15`/`F18`/`F20`/`F22`/`COLOMBIA_COMPLIANCE_TRACEABILITY.md`,
   todas 2026-08-09) — usada con verificación de vigencia; 4 hallazgos de drift confirmados
   (ver `CROSS_APP_INTEGRATION_MATRIX.md` y `ACCOUNTING_FLOW_MATRIX.md`).

**Regla aplicada:** cuando existe divergencia entre documentación y código real, se registra
como DOCUMENTATION_DRIFT explícitamente (no se oculta, no se re-implementa desde la doc vieja).

## APP_INVENTORY — 17 apps reales bajo `apps/tenant/`

Verificado con `ls apps/tenant/` (no asumido de memoria ni de documentación previa):

```
bancos, clientes, compras, contabilidad, core, cotizaciones, dashboard,
empleados, empresa, facturas, gastos, inventario, landing, perfil,
proveedores, proyectos, ventas
```

Coincide con las "16 apps" de las 2 misiones de auditoría previas (que excluyen
`landing`, app de aterrizaje pública, no un módulo de negocio transaccional).
Ninguna app nueva encontrada — no se crean apps nuevas en esta misión (regla
explícita §62/§88 del prompt maestro).

## Estado de auditoría previa por app (heredado, no re-ejecutado de cero)

Las 16 apps de negocio ya pasaron por **2 ciclos completos de auditoría de
código/arquitectura/dead-code** (`APP_AUDIT_MASTER_FINAL.md` 2026-08-21,
`F34_MASTER_FINAL.md` mismo día) con regresión de tests propia y 0 fallos
nuevos introducidos. Esta auditoría (empresarial/contable/tributaria/de
controles) es una **lente distinta y complementaria**, no una repetición —
se apoya en esa base ya verificada para el código muerto/arquitectura y se
enfoca en: coherencia contable/tributaria, controles internos, integridad de
datos de negocio, UX empresarial, y consolidación en las 10 matrices que el
prompt maestro exige explícitamente.

Además, 4 apps (`cotizaciones`, `proveedores`, `inventario`) recibieron
**misiones de modernización dedicadas adicionales en esta misma sesión**
(2026-08-27, posteriores a las auditorías de código de 2026-08-21), con
correcciones reales commiteadas — la evidencia más reciente disponible para
esas 3 apps proviene de esas misiones, no de los docs de 2026-08-21/08-09.

## MODEL_INVENTORY — modelos clave por dominio (no exhaustivo, los ya inventariados en auditorías previas)

| Dominio | Modelos clave |
|---|---|
| Terceros | `Cliente`, `ClienteContacto`, `Proveedor` |
| Comercial | `Cotizacion`, `Producto`/`Servicio` (x2: `cotizaciones` y `inventario`, no unificados) |
| Compras | `OrdenCompra`, `RecepcionCompra`, `RecepcionCompraItem`, `PlantillaOrdenCompra` |
| Inventario | `CategoriaItem`, `Producto`, `Servicio`, `ActivoFijo`, `MovimientoInventario`, `TrasladoInventario`, `HistorialServicio` |
| Ventas | `Venta`, `ItemVenta`, `ResolucionFacturacion` |
| Facturación | `Factura`, `NotaCredito`, `ItemNotaCredito`, `FacturaAnexos` |
| Gastos | `DocumentoSoporte`, `ResolucionDIAN` |
| Nómina | `Empleado`, `Contrato`, `Devengo`, `TransmisionNominaDIAN` |
| Bancos | `CuentaBancaria`, `ExtractoBancario`, `TransaccionBancaria` |
| Contabilidad | `CuentaContable`, `AsientoContable`, `MovimientoContable`, `ConfiguracionRetenciones`, `Retencion`, `ReglaContable`, `PeriodoContable`, `CatalogoMaestroNIIF` |
| Proyectos | `Proyecto` |

## SERVICE_INVENTORY — capa de servicios confirmada como Pull Model consistente

Verificado en las 2 auditorías previas + esta sesión: `contabilidad` es la
única propietaria del mapeo PUC (`ReglaContable`); `RetencionesService`
(`contabilidad`) es la única fuente real de cálculo de retenciones; ninguna
app de negocio crea `AsientoContable` directamente. Ver
`ACCOUNTING_FLOW_MATRIX.md` para el detalle completo.

## CROSS_APP_INVENTORY / DOCUMENT_INVENTORY

Ver `CROSS_APP_INTEGRATION_MATRIX.md` (17 relaciones cross-app documentadas
con evidencia) y `BUSINESS_DEPENDENCY_GRAPH.md` (misma información en lente
de negocio: REQUIRED/CONDITIONAL/OPTIONAL/DERIVED/REFERENCE/TRIGGER).

## ACCOUNTING_INVENTORY / TAX_INVENTORY

Ver `ACCOUNTING_FLOW_MATRIX.md` y `TAX_COMPLIANCE_MATRIX.md`.

## DOCUMENTATION_DRIFT registrado en esta fase (código real diverge de docs 2026-08-09)

| # | Doc antiguo | Afirmación 2026-08-09 | Realidad 2026-08-27 |
|---|---|---|---|
| 1 | `F18_COLOMBIAN_BUSINESS_FLOWS.md` §F18.6 | "Compras → Inventario: no implementado" | Implementado — `RecepcionCompraBusinessService` llama `KardexService.registrar_movimiento()` |
| 2 | `F18_COLOMBIAN_BUSINESS_FLOWS.md` §F18.11 | "Traslado entre sedes: no implementado" | Implementado — `TrasladoInventario` + `TrasladoInventarioService`, F21 |
| 3 | `F22_ACCOUNTING_CONTRACT.md` §1 | "SALIDA_VENTA: mecanismo listo, sin datos reales aún" | Generándose en producción — `ventas._generar_salida_inventario()` |
| 4 | `COLOMBIA_COMPLIANCE_TRACEABILITY.md` | "Notas crédito — referencia a documento origen no auditada" | Implementado con test real — `ItemNotaCredito` + `ENTRADA_DEVOLUCION` |

Estos 4 no se re-implementan (ya existen) — se corrige el registro documental
para que una fase futura no los redescubra ni los trate como pendientes.

## Qué NO se modificó en esta FASE 0

Ningún archivo de código fue tocado. Esta fase es exclusivamente lectura,
mapeo y clasificación, consistente con la regla explícita del prompt maestro
(§88: "Primero: AUDITAR, MAPEAR, CLASIFICAR. Después: CORREGIR").
