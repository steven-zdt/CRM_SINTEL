# Reporting Hub — Catalogo de Datasets

**Fecha:** 2026-08-26
**Fuente de verdad real:** `GET /api/v1/reporting/` (este documento es una foto, el endpoint es la SSoT viva).

---

## `ventas.resumen`

| | |
|---|---|
| **Owner app** | `ventas` |
| **Provider** | `apps/tenant/ventas/reporting/provider.py::VentasReportProvider` |
| **Descripcion** | Ventas agregadas por fecha, cliente y/o estado. |
| **Dimensiones** | `fecha` (DATE, `fecha_emision`), `cliente` (STRING, `cliente__razon_social`), `estado` (STRING) |
| **Medidas** | `cantidad_ventas` (COUNT), `subtotal` (SUM), `impuestos` (SUM), `total` (SUM, `total_neto`) |
| **Filtros** | `fecha_inicio`, `fecha_fin`, `cliente_id`, `estado` (todos opcionales) |
| **Scope** | `empresa` unicamente — `Venta` no tiene campo `sede`/`area` |
| **Export** | json, csv, xlsx |
| **Validado en vivo** | Si — tenant `home`, 1 venta real BORRADOR $23,800, agrupado por estado |

## `contabilidad.balance_prueba`

| | |
|---|---|
| **Owner app** | `contabilidad` |
| **Provider** | `apps/tenant/contabilidad/reporting/provider.py::ContabilidadReportProvider` |
| **Descripcion** | Adapter de solo lectura sobre `balance_prueba_selector` — el calculo permanece en Contabilidad. |
| **Dimensiones** | `codigo` (STRING), `nombre` (STRING) — informativas, el desglose siempre es completo |
| **Medidas** | `saldo_anterior`, `debito`, `credito`, `nuevo_saldo` (todas SUM) |
| **Filtros** | `fecha_inicio` (obligatorio), `fecha_fin` (obligatorio) |
| **Scope** | `empresa` unicamente |
| **Export** | json, csv, xlsx |
| **Validado en vivo** | Si — tenant `home`, periodo 2026-08/09, cifras identicas a la validacion en vivo de CONT-19 (6 cuentas, debito=credito=$3,050,000) |

## `tax.iva`

| | |
|---|---|
| **Owner app** | `facturas` |
| **Provider** | `apps/tenant/facturas/reporting/provider.py::FacturasTaxReportProvider` |
| **Descripcion** | IVA generado (ventas) y descontable (compras), desde `FacturaImpuesto`. Detalle completo: `docs/tax/TAX_DATASETS.md`. |
| **Validado en vivo** | Si — catalogo/detalle/query contra `home` (vacio, real: 0 filas confirmadas por consulta directa a BD); validacion funcional completa via test con datos reales |

## `tax.retenciones`

| | |
|---|---|
| **Owner app** | `contabilidad` |
| **Provider** | `apps/tenant/contabilidad/reporting/provider.py::ContabilidadReportProvider` |
| **Descripcion** | RETEFUENTE/RETEICA/RETEIVA, desde `Retencion` (SSoT real de `RetencionesService`). Detalle completo: `docs/tax/TAX_DATASETS.md`. |
| **Validado en vivo** | Si — catalogo/detalle/query contra `home` (vacio, real); validacion funcional completa via test con datos reales, incluida una reversa |

## `inventario.movimientos`

| | |
|---|---|
| **Owner app** | `inventario` |
| **Provider** | `apps/tenant/inventario/reporting/provider.py::InventarioReportProvider` |
| **Descripcion** | Entradas/salidas/traslados de producto (Kardex), leidos de `MovimientoInventario` — `KardexService` sigue siendo el SSoT de escritura. Escopeado a movimientos de producto (`producto__isnull=False`); movimientos de ActivoFijo quedan fuera (dominio distinto). |
| **Dimensiones** | `fecha`, `sede`, `producto`, `categoria`, `tipo` |
| **Medidas** | `cantidad_movimientos` (COUNT), `cantidad` (SUM), `costo_total` (SUM de `cantidad × costo_unitario`) |
| **Filtros** | `fecha_inicio`, `fecha_fin`, `tipo`, `producto_id` |
| **Scope** | `empresa`, `sede` |
| **Export** | json, csv, xlsx |
| **Validado en vivo** | Si — catalogo/detalle contra `home` (vacio, real); validacion funcional completa via test con datos reales (`KardexService.registrar_movimiento`, ENTRADA_COMPRA + SALIDA_VENTA) |
| **Deliberadamente no incluido** | medida "stock actual" — es un saldo/snapshot, no un dato agregable por periodo; se deja como dataset futuro si hay demanda real |
| **Bug real encontrado y corregido** | alias de medida `cantidad` colisionaba con el campo real `MovimientoInventario.cantidad` dentro de la medida compuesta `costo_total` — ver `REPORTING_ARCHITECTURE.md` §8.1 |

## `gastos.resumen`

| | |
|---|---|
| **Owner app** | `gastos` |
| **Provider** | `apps/tenant/gastos/reporting/provider.py::GastosReportProvider` |
| **Descripcion** | `DocumentoSoporte` agregado por fecha, sede, categoria contable y/o proveedor. No incluye IVA (el modelo no lo tiene, confirmado en la mision Tax Service) ni retenciones (ver `tax.retenciones`). |
| **Dimensiones** | `fecha`, `sede`, `categoria_contable`, `proveedor` |
| **Medidas** | `cantidad_documentos` (COUNT), `subtotal` (SUM), `total` (SUM) |
| **Filtros** | `fecha_inicio`, `fecha_fin`, `categoria_contable`, `proveedor_id` |
| **Scope** | `empresa`, `sede` |
| **Export** | json, csv, xlsx |
| **Validado con datos reales** | Si — test con 3 `DocumentoSoporte` reales (incluido uno `anulado=True` que correctamente no cuenta) |

## `facturas.resumen`

| | |
|---|---|
| **Owner app** | `facturas` |
| **Provider** | `apps/tenant/facturas/reporting/provider_resumen.py::FacturasResumenReportProvider` |
| **Descripcion** | Todas las Facturas/Notas (cualquier `estado` y `tipo`), a diferencia de `tax.iva` que solo cuenta `ACEPTADA`. Visibilidad operativa del ciclo documental completo. |
| **Dimensiones** | `fecha`, `naturaleza`, `estado`, `tipo` (FE/NC/ND) |
| **Medidas** | `cantidad_documentos` (COUNT), `subtotal` (SUM), `impuestos` (SUM), `total` (SUM) |
| **Filtros** | `fecha_inicio`, `fecha_fin`, `naturaleza`, `estado`, `tipo` |
| **Scope** | `empresa`, `sede` |
| **Export** | json, csv, xlsx |
| **Validado con datos reales** | Si — test con 3 Facturas reales (VENTA ACEPTADA, COMPRA ACEPTADA, VENTA RECHAZADA), confirma que RECHAZADA SI cuenta aqui (comportamiento inverso a `tax.iva`) |
| **Deliberadamente no incluido** | medida "saldo pendiente" — `Factura.saldo_pendiente` es una property que consulta `BancosBridge` por factura individual (1 query/fila); no existe metodo bulk, construirlo duplicaria logica de Bancos. Diferido si Bancos expone un metodo bulk real. |

## Diferidos (no registrados todavia)

`empleados.*`, `contabilidad.estado_resultados`, `contabilidad.libro_diario` — ver `REPORTING_ARCHITECTURE.md` §9 para la razon de cada diferimiento y §8 para el procedimiento de alta.

---

## Governance (FASE 35)

| Check | Resultado |
|---|---|
| `manage.py check` | System check identified no issues (0 silenced) — verificado tras cada cambio, incluida la version final |
| `git diff --check` | Sin errores de whitespace |
| Tests dirigidos | `tests/services/reporting/test_query_engine.py` (registry + validacion de catalogo, sin BD) + `apps/tenant/ventas/tests/test_reporting_provider.py` (registro real via AppConfig.ready, query real, scope SEDE bloqueado/permitido) |
| Bug encontrado y corregido durante la construccion | Regex de `pk` de DRF excluye `.`, rompia el lookup de `dataset_id` con notacion `app.dataset` — ver `REPORTING_ARCHITECTURE.md` §7 |
