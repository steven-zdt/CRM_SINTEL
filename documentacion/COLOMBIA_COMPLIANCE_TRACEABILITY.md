# Matriz de Trazabilidad Colombiana

**Fecha:** 2026-08-09
**Advertencia obligatoria (§29 del prompt maestro, no negociable):** esta matriz representa
**cobertura técnica verificada por lectura de código**, nunca certificación jurídica. Ninguna fila
implica que SINTEL cumple una norma colombiana específica — implica que el mecanismo técnico
descrito existe y fue verificado en el código real, citado con archivo:línea. La verificación de
cumplimiento legal real requiere revisión por un profesional/asesor legal-tributario colombiano
con acceso a las fuentes oficiales vigentes, fuera del alcance de esta sesión.

| Área normativa (referencia general, no citación verificada) | Proceso | App | Servicio/Modelo real | Evidencia (archivo) | Cobertura técnica |
|---|---|---|---|---|---|
| Facturación electrónica DIAN | Emisión de Factura | `facturas` | `Factura` (`Estado`: BORRADOR/ENVIADA/ACEPTADA/RECHAZADA/ANULADA), `cufe` | `apps/tenant/facturas/models.py:26-31,164` | 🟡 Estados y CUFE existen; transiciones no auditadas exhaustivamente |
| Facturación electrónica DIAN | Ventas → Factura | `ventas`→`facturas` | `FacturaBusinessService.crear_factura_desde_venta()` | `documentacion/VENTAS_FACTURAS_AUDIT.md` | 🟢 Contrato verificado con evidencia real |
| Nómina electrónica DIAN | Documento de nómina | `empleados` | `TransmisionNominaDIAN` (modelo separado de `Devengo`) | `documentacion/F18_COLOMBIAN_BUSINESS_FLOWS.md` §F18.9 | 🟢 Separación de conceptos verificada |
| Contabilidad (marco técnico normativo) | Asientos contables | `contabilidad` | `Contabilizador`, Pull Model, `APP_ORIGEN_PREFIJOS` | `documentacion/arquitectura_general.md` §6 | 🟢 Arquitectura Pull verificada; sin concepto `RegulatoryVersion`/Grupo 1-2-3 implementado |
| Protección de datos personales | Terceros (clientes/proveedores/empleados) | `clientes`/`proveedores`/`empleados` | Aislamiento por schema PostgreSQL (`django-tenants`) | `documentacion/arquitectura_general.md` §3.1 | 🟡 Aislamiento técnico entre tenants verificado; sin auditoría específica de minimización/consentimiento de datos personales en esta fase |
| Conciliación bancaria / estado de pago de Factura | Pago de Factura | `facturas`↔`bancos` | `business_service.py:915-928` (rechaza `PAGADA` sin conciliación 100%) | `documentacion/F18_COLOMBIAN_BUSINESS_FLOWS.md` §F18.3 | 🟢 Control verificado con código real |

## Qué NO está en esta matriz (explícito, no oculto)

- Documento equivalente electrónico — no implementado en el código actual.
- Clasificación Grupo 1/2/3 (Decreto 2420/701) — no implementado.
- `RegulatoryVersion` (versión normativa vigente/reemplazada) — no implementado (el §4.1 del
  prompt maestro lo condiciona a "únicamente si ya existe un mecanismo compatible"; no existe).
- Notas crédito/débito — referencia al documento origen no auditada en esta fase.
- Auditoría específica de Ley 1581 (minimización de datos, consentimiento, derechos ARCO) — fuera
  de alcance, requiere revisión legal-funcional dedicada, no solo lectura de modelos.
