# Tax Service — Arquitectura

**Fecha:** 2026-08-26
**Estado:** TAX_REPORTING = COMPLETED_WITH_DEFERRED (ver §"Decision Final")

---

## 1. Principio central

**Una responsabilidad = una fuente de verdad (Regla Absoluta #1).** El Tax Service no posee ningun dato tributario -- lee `Retencion` (Contabilidad) y `FacturaImpuesto` (Facturas), ambos ya existentes y ya siendo escritos por sus dueños reales (`RetencionesService`, el parser/importador de Facturas). No se movio, copio, ni duplico ningun modelo.

## 2. Decision arquitectonica central: sin `apps/services/tax/` ni contrato paralelo

La mision pedia evaluar un "TaxDataset Contract"/"TaxReportProvider" (FASE 4/5). **Se decidio NO crear un tipo Python nuevo**: ya existe `ReportDataset`/`ReportField`/`ReportMeasure`/`ReportProvider` (mision Reporting Hub, `apps/services/reporting/contracts.py`) -- crear un segundo contrato para "datasets fiscales" habria violado la misma Regla Absoluta #1 que esta mision exige. El "TaxDataset Contract" se satisface como una CONVENCION documentada (`TAX_DATASETS.md`) sobre el contrato ya existente.

Consecuencia: **no existe `apps/services/tax/`**. Los datasets fiscales viven como providers adicionales en las apps dueñas del dato, mismo patron que `ventas.resumen`/`contabilidad.balance_prueba` (mision Reporting Hub):

| Dataset | Vive en | Extiende |
|---|---|---|
| `tax.iva` | `apps/tenant/facturas/reporting/provider.py` (nuevo) | Nuevo `FacturasTaxReportProvider` |
| `tax.retenciones` | `apps/tenant/contabilidad/reporting/provider.py` (ya existia) | `ContabilidadReportProvider` (ahora expone 2 datasets) |

## 3. Flujo real

```
Retencion (Contabilidad, SSoT)          FacturaImpuesto (Facturas, SSoT)
    v                                        v
ContabilidadReportProvider              FacturasTaxReportProvider
    v                                        v
         ReportRegistry (Reporting Hub, sin cambios)
                        v
         ReportQueryEngine (validacion + Scope Engine, sin cambios)
                        v
                   ReportResult
                        v
         JSON / CSV / XLSX (Reporting Hub, sin cambios)
```

Cero codigo nuevo en `apps/services/reporting/` -- el nucleo transversal ya construido en la mision anterior se reutilizo tal cual, confirmando que fue diseñado correctamente para este tipo de expansion (FASE 40/44, "loop continuo").

## 4. Bug real encontrado y corregido durante el diseño

Al trazar a mano la matematica de una retencion reversada (para escribir el test de regresion, no en produccion) se encontro que filtrar `reversada=False` -- el mismo criterio que usa `RetencionesService.total_retenciones_por_documento()`, correcto para el saldo de UN documento -- **subcuenta en una agregacion por periodo/tipo** cuando la reversa se atribuye a un documento distinto del original (el caso real: una Nota Credito reversando la retencion de la Factura que reemplaza). El original queda excluido (ya `reversada=True`) sin que su reversa lo compense en la misma consulta. Corregido: `tax.retenciones` suma TODAS las filas sin filtrar `reversada` -- el original conserva su valor real y la reversa ya viene negativa, asi que la suma neta correctamente sin importar en que documento/periodo caiga cada lado. Detalle completo en `TAX_DATASETS.md`.

## 5. Verificacion con datos reales

El tenant `home` (usado en las 3 misiones anteriores de esta sesion) tiene **cero filas reales** en `Retencion` y `FacturaImpuesto` hoy (confirmado por consulta directa a la base de datos) -- los datos de demo de misiones anteriores pasaron por `Contabilizador`/`ImpuestoDocumento`, un camino de escritura DISTINTO (ver `TAX_BASELINE.md` §3). En vez de escribir mas datos reales al tenant demo (que en misiones anteriores requirio autorizacion explicita cada vez por ser una accion de escritura financiera), la validacion funcional se hizo con **tests Django reales** (`test_tax_iva_provider.py`, `test_tax_retenciones_provider.py`) que crean datos reales via los servicios de escritura reales (`RetencionesService.crear_retencion()`/`reversar_retencion()`, `FacturaImpuesto.objects.create()`) en un esquema de tenant de prueba aislado -- mismo nivel de rigor, sin tocar el tenant demo. Ambos datasets tambien se confirmaron en vivo contra `home` (catalogo, detalle, query) -- correctamente vacios, no un error.

## 6. Deuda diferida (explicita, no oculta)

| Item | Por que se difiere |
|---|---|
| `tax.reteica`/`tax.reteiva` como datasets separados | Consolidados deliberadamente en `tax.retenciones` con `tipo` como dimension/filtro -- evita 3 providers casi identicos; el usuario obtiene el mismo resultado filtrando/agrupando por `tipo` |
| `tax.resumen` (IVA + retenciones combinados) | Sin consumidor UI real que lo pida todavia; un tercer provider agregador sin fuente propia es prematuro |
| Conciliacion formal documento vs. contabilizado (FASE 12) | Sin evidencia de un vinculo garantizado 100% entre `Retencion`/`FacturaImpuesto` y `MovimientoContable`/`ImpuestoDocumento` para todo tipo de documento -- ver `TAX_RECONCILIATION.md` |
| Conciliacion con Bancos / estado PAGADO (FASE 13/14) | Gap confirmado: `TransaccionBancaria` no tiene ningun vinculo a impuestos hoy -- construirlo seria inventar una regla de negocio |
| Alertas (FASE 28) | Dependen de la conciliacion formal, diferida por la misma razon |
| Centro Tributario / Dashboard fiscal dedicado (FASE 15-17) | Ambos datasets ya son consultables via el catalogo generico "📊 Reportes" (mision Reporting Hub Frontend) sin trabajo adicional -- una pantalla dedicada con filtros/KPI propios (como la de Ventas) queda para cuando exista demanda real de esa UX especifica |
| `compras.ItemOrdenCompra.valor_iva` en `tax.iva` | Riesgo de doble conteo con `FacturaImpuesto` no descartado con evidencia -- ver `TAX_BASELINE.md` §1 |
| Otros impuestos (INC, estampillas, etc.) (FASE 10) | Sin evidencia de que existan registros reales de estos conceptos en el sistema hoy; no se construye "framework de todos los impuestos" por anticipado |
| `null` en vez de `0` en totales sobre queryset vacio | Comportamiento heredado del Reporting Hub (`Sum()` de Django sobre queryset vacio devuelve `None`) -- no es un bug de Tax Service, pero se deja anotado como mejora cosmetica futura del nucleo transversal |

## 7. Decision sobre `apps/tenant/impuestos` (FASE 32/33)

**No se crea.** La auditoria (FASE 0-3) no encontro evidencia de necesidad real de persistir `ObligacionTributaria`, `PeriodoFiscal`, `Declaracion`, `PagoTributario`, ni `Compensacion` -- ninguno de estos conceptos existe hoy en el sistema, y construirlos sin un caso de uso real (una declaracion formal que presentar, un vencimiento que rastrear) seria exactamente lo que Regla Absoluta #7 prohibe. El gap real encontrado (Bancos sin vinculo a impuestos) es una PRECONDICION para esa capacidad, no evidencia de que deba construirse ahora -- se documenta como bloqueante para una fase futura, no se resuelve con una app nueva especulativa.

## 8. Release Gate (FASE 42)

- [x] IVA generado
- [x] IVA descontable
- [x] IVA neto calculado (`saldo_fiscal_calculado`, etiquetado correctamente como calculado, no como valor a pagar)
- [x] Retefuente
- [x] ReteICA
- [x] ReteIVA
- [x] Reversas (bug real encontrado y corregido, con test de regresion)
- [ ] Conciliacion -- diferida, sin evidencia de vinculo confiable (ver §6)
- [x] Reporting Hub (2 datasets nuevos registrados, cero cambios al nucleo)
- [x] User Context / scope (via `OrganizationalScope`, sin RBAC nuevo)
- [x] Tenant isolation / empresa / sede (segun campos reales de cada modelo -- `tax.iva` tiene sede via Factura, `tax.retenciones` no la tiene porque `Retencion` no la tiene)
- [x] Export (JSON/CSV/XLSX, reutiliza el Reporting Hub sin exportador nuevo)
- [ ] Dashboard fiscal dedicado -- diferido (ver §6)
- [x] Documentacion (este documento + BASELINE + DATASETS + RECONCILIATION)
- [x] Governance (`manage.py check` limpio, sin drift de migraciones, tests dirigidos pasando)

## 9. Estado final (FASE 43)

**TAX_REPORTING = COMPLETED_WITH_DEFERRED**

No existe necesidad demostrada de obligaciones/declaraciones (FASE 32 concluyo negativo con evidencia real) -- por lo tanto NO aplica `TAX_DOMAIN = COMPLETED`. El nucleo de Tax Reporting (IVA + retenciones, con reversas correctamente netadas) esta completo, probado con datos reales, y expuesto via el Reporting Hub sin duplicar ninguna infraestructura existente. La deuda diferida (§6) es explicita y esta bloqueada por gaps reales del sistema (Bancos), no por falta de tiempo.
