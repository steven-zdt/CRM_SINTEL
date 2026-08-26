# Tax Service — Baseline (FASE 0/1/2/3)

**Fecha:** 2026-08-26
**Alcance:** auditoria real de codigo (modelos, servicios, selectors) antes de construir nada. Ningun codigo se modifico durante esta fase.

---

## 1. Matriz de datos tributarios (FASE 1)

| Concepto | SSoT | App | Modelo | Se calcula en | Se contabiliza en | Se paga en |
|---|---|---|---|---|---|---|
| IVA generado (ventas) | Facturas | `facturas` | `FacturaImpuesto` (tipo='IVA') + `Factura.naturaleza='VENTA'` | Facturas (parser XML / captura manual) | Contabilidad (`Contabilizador`, via `ImpuestoDocumento`) | **Sin evidencia** (ver §6) |
| IVA descontable (compras) | Facturas | `facturas` | `FacturaImpuesto` (tipo='IVA') + `Factura.naturaleza='COMPRA'` | Facturas | Contabilidad | **Sin evidencia** |
| IVA en `compras.ItemOrdenCompra` | Compras | `compras` | `ItemOrdenCompra.valor_iva` | Compras | — (no confirmado si contabiliza via Retencion/ImpuestoDocumento) | — |
| Retefuente | Contabilidad | `contabilidad` | `Retencion` (tipo='RETEFUENTE') | `RetencionesService` (Pull Model, llamado desde Facturas/Compras/Gastos) | `asiento_contable` FK en `Retencion` | **Sin evidencia** |
| ReteICA | Contabilidad | `contabilidad` | `Retencion` (tipo='RETEICA') | idem | idem | **Sin evidencia** |
| ReteIVA | Contabilidad | `contabilidad` | `Retencion` (tipo='RETEIVA') | idem | idem | **Sin evidencia** |
| Configuracion de tarifas aplicadas (tenant) | Contabilidad | `contabilidad` | `TarifaImpuesto`, `ConfiguracionRetenciones` | — | — | — |
| Catalogo DIAN (normativa) | Public | `apps.public.impuestos` | `TipoImpuesto`, `TarifaIVA`, `ConceptoRetencion` | — (referencia, no aplicado) | — | — |

**REVIEW / BLOCKED (Regla Absoluta #7):** `compras.ItemOrdenCompra.valor_iva` es una fuente de IVA descontable POTENCIALMENTE distinta de `FacturaImpuesto` (compra con naturaleza=COMPRA) -- no hay evidencia en el codigo de si una compra real genera AMBOS registros (doble conteo si se suman ambos) o si son mutuamente excluyentes segun si el proveedor esta registrado en DIAN. **No se incluye `compras.ItemOrdenCompra` en el dataset `tax.iva` de esta pasada** hasta auditar esa relacion con evidencia real -- se documenta como pendiente, no se asume.

## 2. Naturaleza fiscal (FASE 2)

| Naturaleza | Campo real | Significado confirmado |
|---|---|---|
| GENERADO | `FacturaImpuesto.tipo='IVA'` + `Factura.naturaleza='VENTA'` | IVA que la empresa cobra a sus clientes |
| DESCONTABLE | `FacturaImpuesto.tipo='IVA'` + `Factura.naturaleza='COMPRA'` | IVA que la empresa paga a sus proveedores (deducible) |
| RETENIDO_A_TERCERO (practicada) | `Retencion.naturaleza='COMPRA'` | La empresa retiene al pagar a un proveedor |
| RETENIDO_A_EMPRESA (sufrida) | `Retencion.naturaleza='VENTA'` | El cliente retiene al pagar a la empresa |

**Hallazgo textual confirmado** (docstring real, `models.py:1056-1062`): *"VENTA: retencion requerida por el cliente. COMPRA: retenida al proveedor."* -- el campo `naturaleza` de `Retencion` es el UNICO discriminador; no existe un booleano separado `practicada`/`sufrida`. Se reutiliza tal cual, sin inventar un campo nuevo.

**Advertencia de diseño:** `naturaleza` se usa con el MISMO nombre en `Factura`/`Retencion`/`ConfiguracionRetenciones` para "tipo de transaccion" (VENTA/COMPRA) -- no es un bug, pero el Tax Service debe ser explicito en su documentacion sobre que este campo NO distingue "IVA generado vs descontable" por si mismo salvo combinado con el `tipo` de impuesto.

## 3. Retencion vs ImpuestoDocumento -- no son duplicados, son capas distintas

- **`Retencion`** (`contabilidad/models.py:951-1103`): el LIBRO de retenciones real, escrito EXCLUSIVAMENTE por `RetencionesService` (confirmado: unicos call-sites de `Retencion.objects.create()`/`Retencion(...)` son `retenciones_service.py:189,451` y comandos de migracion one-time). Tiene reversal chain propio (`reversada` + `retencion_reversada_por`), independiente de si el documento ya se contabilizo (`asiento_contable` es nullable).
- **`ImpuestoDocumento`** (`contabilidad/models.py:1290-1363`): registro de la CONTABILIZACION de cualquier impuesto (tipo libre: IVA_GENERADO, IVA_DESCONTABLE, RETEFUENTE, etc.), creado EXCLUSIVAMENTE por `Contabilizador` (`integracion/contabilizador.py:216,391`) a partir del DTO `TransaccionEconomica.impuestos`. Requiere `asiento` (FK obligatorio) -- no existe sin contabilizacion.

**Conclusion:** no hay duplicacion real que eliminar (Regla Absoluta #29) -- son dos capas del mismo dato (retencion "de negocio" vs. su reflejo contable), coherente con el resto de la arquitectura Pull Model de este proyecto. El Tax Service debe leer `Retencion` para retenciones (ya tiene todo lo necesario: base/tarifa/monto/naturaleza/reversal) y NO necesita tocar `ImpuestoDocumento` para retenciones. Para IVA, sin embargo, `Retencion` NO aplica (`Retencion.tipo` no incluye "IVA" plano) -- la fuente real de IVA es `FacturaImpuesto` (ver §1).

## 4. `apps/public/impuestos` -- NO es un catalogo duplicado (Regla Absoluta #3 verificada, sin hallazgo)

Confirmado: modelos `models.Model` planos (NO `SintelTenantBaseModel`, sin FK `empresa`), esquema `public`, docstring explicito: *"Esta biblioteca legal esta disponible para todos los tenants"*. Es el catalogo DIAN de referencia (`TipoImpuesto`, `TarifaIVA`, `ConceptoRetencion`, + 6 modelos normativos mas). `contabilidad.TarifaImpuesto` es la tarifa APLICADA por el tenant (empresa-scoped, versionada por fecha via `vigente_en()`, incluye conceptos no-DIAN como nomina/parafiscales). Son capas distintas del mismo dominio (catalogo vs. config aplicada) -- **no se encontro duplicacion que consolidar.**

## 5. Gastos y Compras -- gaps reales, no inventados

- **`DocumentoSoporte` (gastos): CERO campos de IVA.** Confirmado por lectura completa del modelo -- el mecanismo "documento soporte" (compra a no obligados a facturar) no maneja IVA en este sistema. Las retenciones si existen (propiedades `total_retefuente`/`total_reteica`/`total_reteiva` que leen `Retencion` via Pull Model).
- **`compras.OrdenCompra`/`ItemOrdenCompra`: tiene `porcentaje_iva`/`valor_iva`** a nivel de item, pero SIN campos de retencion propios -- las retenciones de compras tambien viven en `Retencion` (`documento_origen_app='compras'`). Relacion con `FacturaImpuesto` sin confirmar (ver REVIEW en §1).

## 6. Bancos -- gap confirmado, no hay vinculo a pagos tributarios

`TransaccionBancaria` (`bancos/models.py`, leido completo) solo tiene soft-references UUID a `factura`/`proveedor`/`cliente`, mas `conciliado`/`notas_conciliacion` (conciliacion MANUAL, generica). **No existe ningun campo que vincule una transaccion bancaria a una retencion, un IVA, ni a una obligacion DIAN.** Consecuencia directa para el diseño (FASE 13/14): el Tax Service **no puede** determinar "PAGADO" con evidencia real hoy. Se documenta como limitacion explicita, no se inventa un mecanismo de conciliacion bancaria-fiscal.

## 7. No existe hoy ningun reporte/dashboard de IVA o retenciones

Confirmado por auditoria completa de `contabilidad/services/selectors.py` (solo `balance_prueba_selector`, `estado_resultados_selector`, `get_libro_diario_periodo` existen) y `apps/tenant/dashboard/` (sin logica fiscal real). El Tax Service que se construye en esta mision es la PRIMERA capacidad de este tipo en el proyecto.

## 8. Decision arquitectonica resultante (FASE 4, adelantada)

**No se crea un contrato `TaxDataset` nuevo y paralelo.** Ya existe `ReportDataset`/`ReportField`/`ReportMeasure`/`ReportProvider` (mision Reporting Hub, `apps/services/reporting/contracts.py`) -- crear un segundo tipo de contrato para "datasets fiscales" violaria la misma regla de no-duplicacion que esta mision exige. El "TaxDataset Contract" de la FASE 4 se satisface como una CONVENCION de nombres de dimension/medida sobre el contrato ya existente (`tax_type`, `nature`, `accounting_status`, etc.), documentada en `docs/tax/TAX_DATASETS.md`, no como codigo nuevo.

**Providers de datasets fiscales viven en la app dueña del dato real** (mismo patron que Ventas/Contabilidad en la mision anterior):
- `tax.retenciones` -> `apps/tenant/contabilidad/reporting/provider.py` (extiende `ContabilidadReportProvider` ya existente) -- fuente: `Retencion`.
- `tax.iva` -> `apps/tenant/facturas/reporting/provider.py` (nuevo) -- fuente: `FacturaImpuesto` + `Factura.naturaleza`.

**No se crea `apps/tenant/impuestos`** en esta pasada -- ver FASE 32/33 en `docs/tax/TAX_ARCHITECTURE.md` §"Decision sobre apps/tenant/impuestos" para la justificacion final.
