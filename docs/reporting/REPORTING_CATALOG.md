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

## Diferidos (no registrados todavia)

`inventario.*`, `facturas.*`, `gastos.*`, `empleados.*`, `contabilidad.estado_resultados`, `contabilidad.libro_diario` — ver `REPORTING_ARCHITECTURE.md` §9 para la razon de cada diferimiento y §8 para el procedimiento de alta.

---

## Governance (FASE 35)

| Check | Resultado |
|---|---|
| `manage.py check` | System check identified no issues (0 silenced) — verificado tras cada cambio, incluida la version final |
| `git diff --check` | Sin errores de whitespace |
| Tests dirigidos | `tests/services/reporting/test_query_engine.py` (registry + validacion de catalogo, sin BD) + `apps/tenant/ventas/tests/test_reporting_provider.py` (registro real via AppConfig.ready, query real, scope SEDE bloqueado/permitido) |
| Bug encontrado y corregido durante la construccion | Regex de `pk` de DRF excluye `.`, rompia el lookup de `dataset_id` con notacion `app.dataset` — ver `REPORTING_ARCHITECTURE.md` §7 |
