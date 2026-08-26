# Tax Service — Datasets

**Fecha:** 2026-08-26
**Contrato:** convencion de nombres sobre `ReportDataset`/`ReportField`/`ReportMeasure` ya existente (`apps/services/reporting/contracts.py`) -- NO se creo un tipo `TaxDataset` nuevo (ver `TAX_BASELINE.md` §8).

---

## `tax.iva`

| | |
|---|---|
| **Owner app** | `facturas` |
| **Provider** | `apps/tenant/facturas/reporting/provider.py::FacturasTaxReportProvider` |
| **Fuente real** | `FacturaImpuesto` (`tipo_impuesto='IVA'`) + `Factura.naturaleza` + `Factura.estado='ACEPTADA'` |
| **Dimensiones** | `fecha` (DATE, `factura__fecha_emision__date`), `naturaleza` (STRING: VENTA=generado, COMPRA=descontable) |
| **Medidas** | `cantidad_lineas` (COUNT), `base_imponible` (SUM), `valor_iva` (SUM) |
| **Totales especiales** | cuando no se agrupa y se pide `valor_iva`: `iva_generado`, `iva_descontable`, `saldo_fiscal_calculado` (generado - descontable) -- etiquetado explicitamente como SALDO CALCULADO, no como "valor a pagar" |
| **Filtros** | `fecha_inicio`, `fecha_fin`, `naturaleza` |
| **Scope** | `empresa`, `sede` (via `Factura.sede`) |
| **Excluido deliberadamente** | `compras.ItemOrdenCompra.valor_iva` -- riesgo de doble conteo no descartado con evidencia (ver `TAX_BASELINE.md` §1, REVIEW) |
| **Validado con datos reales** | Si -- test `apps/tenant/facturas/tests/test_tax_iva_provider.py` (Factura VENTA + COMPRA + una RECHAZADA que correctamente no cuenta) |

## `tax.retenciones`

| | |
|---|---|
| **Owner app** | `contabilidad` |
| **Provider** | `apps/tenant/contabilidad/reporting/provider.py::ContabilidadReportProvider` (mismo provider que `contabilidad.balance_prueba`) |
| **Fuente real** | `Retencion` (SSoT, escrito exclusivamente por `RetencionesService`) |
| **Dimensiones** | `fecha` (DATE, `created_at__date` -- aproximacion, ver advertencia abajo), `tipo` (RETEFUENTE/RETEICA/RETEIVA), `naturaleza` (VENTA=sufrida, COMPRA=practicada), `documento_origen_app` |
| **Medidas** | `cantidad` (COUNT), `base` (SUM), `monto` (SUM, ya neto de reversas) |
| **Filtros** | `fecha_inicio`, `fecha_fin`, `tipo`, `naturaleza` |
| **Scope** | `empresa` (`Retencion` no tiene sede/area) |
| **Validado con datos reales** | Si -- test `apps/tenant/contabilidad/tests/test_tax_retenciones_provider.py` (RETEFUENTE + RETEICA + una reversa real via `RetencionesService.reversar_retencion()`) |

### Advertencia: `fecha` es `created_at`, no la fecha del documento origen

`Retencion` no tiene un campo `fecha` propio -- es un registro de calculo, no un documento. Se usa `created_at` (cuando el Pull Model creo el registro, tipicamente muy cerca de la fecha real del documento) como aproximacion. Documentado explicitamente, no presentado como "fecha del documento".

### Bug real encontrado y corregido en el diseño: `reversada=False` NO sirve para una agregacion neta

`RetencionesService.total_retenciones_por_documento()` filtra `reversada=False` -- correcto para el saldo de UN documento (excluye el original ya superseded por su reversa). Al trazar la matematica de una reversa ATRIBUIDA A OTRO DOCUMENTO (el caso real: una Nota Credito reversa una retencion de la Factura original, con `documento_reversada_id` distinto), ese mismo filtro APLICADO A UNA AGREGACION POR PERIODO/TIPO subcuenta: excluye el original (ahora `reversada=True`) sin que su reversa (atribuida a otro documento) lo compense en la misma consulta.

**Fix real aplicado:** `tax.retenciones` suma `monto` de TODAS las filas sin filtrar `reversada` -- el original conserva su valor real (positivo) y la fila de reversa ya viene con `monto` negativo (`RetencionesService.reversar_retencion()`, confirmado en el codigo), asi que la suma neta correctamente sin importar en que documento/periodo caiga cada lado del par.

## `contabilidad.balance_prueba` y `ventas.resumen`

Ya documentados en `docs/reporting/REPORTING_CATALOG.md` (mision Reporting Hub) -- no forman parte de esta mision, se listan aqui solo porque comparten el mismo catalogo (`GET /api/v1/reporting/`).

## No implementados en esta pasada (ver `TAX_ARCHITECTURE.md` §Deuda diferida)

`tax.reteica`/`tax.reteiva` como datasets SEPARADOS -- se consolidaron en `tax.retenciones` con `tipo` como dimension/filtro (decision deliberada, no un incumplimiento: evita 3 providers casi identicos, y el usuario puede filtrar/agrupar por `tipo` para obtener exactamente el mismo resultado que 3 datasets separados darian). `tax.resumen` (vista consolidada IVA+retenciones en un solo dataset) -- no construido, cada dataset expone su propio total; consolidarlos requeriria un tercer provider agregador sin fuente de datos propia, evaluado como prematuro sin un consumidor UI real que lo pida.
