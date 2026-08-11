# F26 — Contrato XML → DTO → Modelo → Consumidor

**Fecha:** 2026-08-10

Matriz real (no inventada), basada en `apps/services/document_parser/xml_parser/parser.py`
(pipeline universal), `apps/tenant/facturas/services/business_service.py`
(`guardar_desde_dto`) y `apps/tenant/facturas/models.py`.

| Dato XML (UBL) | Parser | DTO | Persistencia | Consumidor | Acción |
|---|---|---|---|---|---|
| `cbc:ID` (número documento) | Sí | `dto["numero"]` | `Factura.numero` (unique) | Idempotencia por número, UI, referencias cruzadas | KEEP |
| `cbc:UUID` (CUFE/CUDE) | Sí | `dto["identificadores"]["cufe"/"cude"/"uuid"]` | `Factura.cufe` (unique) / `NotaCredito.cude` (unique) | Idempotencia legal (clave DIAN), `fast_get_cufe` pre-validación | KEEP |
| `cac:AccountingSupplierParty` (NIT/razón social emisor) | Sí | `dto["emisor"]` | `Factura.emisor_nit`/`emisor_razon_social`/... (snapshot) | Cálculo de `naturaleza`, DSV, trazabilidad legal (Snapshot Pattern) | KEEP |
| `cac:AccountingCustomerParty` (NIT/razón social receptor) | Sí | `dto["receptor"]` | `Factura.receptor_nit`/`receptor_razon_social`/... (snapshot) | Cálculo de `naturaleza`, DSV, trazabilidad legal | KEEP |
| `cac:LegalMonetaryTotal` (subtotal/impuestos/total) | Sí | `dto["totales"]` | `Factura.subtotal`/`impuestos`/`total` | Contabilidad (vía extractor), reportes, validación matemática | KEEP |
| `cac:InvoiceLine`/`CreditNoteLine` (líneas) | Sí | `dto["items"]` | `ItemFactura`/`ItemNotaCredito` | Inventario (`item_inventario_uuid` resuelto por código), Contabilidad, UI detalle | KEEP |
| `cac:TaxSubtotal` (IVA por línea/documento) | Sí | `item["porcentaje_iva"]`, `dto["impuestos_desglosados"]` | `ItemFactura.porcentaje_iva`/`valor_iva`, `FacturaImpuesto` | Desglose fiscal real, contabilidad | KEEP |
| `cac:WithholdingTaxTotal` (retenciones) | Sí | `item["porcentaje_retefuente"]`/etc. | `ItemFactura.*retefuente/reteiva/reteica` (DEPRECATED, ver F26-004) | Fallback si `RetencionesService` (Pull Model) falla; `migrate_retenciones.py` | DEFER (ver `F26_FINDINGS.md`) |
| `cbc:PaymentMeansCode`/forma de pago | Sí | `dto["forma_pago"]`/`medio_pago_codigo"]` | `Factura.forma_pago`/`medio_pago_codigo` | UI, reportes de cartera | KEEP |
| `cac:PayeeFinancialAccount`/detalles bancarios de pago | Parcial | No mapeado a campo propio | — | Ninguno identificado | E (Ignorar) — Bancos usa `TransaccionBancaria` vía Pull Model (`BancosBridge`), no depende de datos bancarios del XML de factura |
| `UBLVersionID`/`CustomizationID`/`ProfileID`/`ProfileExecutionID` | Sí | `dto[...]` | `Factura.ubl_version`/`customization_id`/`profile_id`/`profile_execution_id` | Auditoría técnica DIAN (poco consumido activamente, pero requerido para reconstrucción del documento si se necesita re-generar XML) | KEEP (categoría D-adyacente: trazabilidad técnica) |
| `sts:DianExtensions` (QR, autorización, validación DIAN) | Sí | `dto["autorizacion"]`, `dto["dian_validation_*"]` | `Factura.qr_code`/`qr_url`/`autorizacion_*`/`dian_validation_*` | Estado DIAN, UI de detalle, auditoría legal | KEEP |
| `ext:UBLExtensions > ApplicationResponse` (XML completo de respuesta DIAN) | Sí | `dto["dian_response_xml"]` | `Factura.dian_response_xml` **y** `FacturaAnexos.application_response_xml` | UI de detalle (vía `FacturaAnexos`) | Redundante — ver F26-005, DEFER |
| XML completo (documento crudo) | N/A (se conserva tal cual) | `xml_text` (parámetro separado, no viaja dentro del `dto`) | `FacturaAnexos.ubl_xml` / `NotaCredito.xml_content` | Trazabilidad legal completa, endpoint `/xml/` dedicado, re-parseo si es necesario | KEEP (mecanismo único, ver `F26_XML_DATA_POLICY.md`) |
| Ruta de archivo en disco del XML original | No (nunca se generó) | No | `Factura.xml_file_path` (ELIMINADO) | Ninguno (0 consumidores confirmados) | **REMOVED** (F26-002) |
| `cac:Signature`/metadata XAdES de firma digital | Parcial | No mapeado a campo propio | — | Ninguno | E (Ignorar) — la validez de la firma es responsabilidad de DIAN al momento de aceptar el documento, SINTEL no re-valida firmas XAdES |

## Regla verificada con datos extra

`ubl_parser.py`/`document_parser/xml_parser/parser.py` usan xpath con `local-name()`
en vez de namespaces fijos precisamente para tolerar variaciones/extensiones de
proveedores DIAN sin romper — cualquier nodo UBL adicional que un proveedor incluya
(no listado en la tabla de arriba) simplemente nunca se busca ni se extrae: no
aumenta el número de campos persistidos, no rompe el parser (xpath no encontrado =
valor por defecto), y no genera registros innecesarios. Confirmado por diseño del
parser (no se requirió una prueba adicional con XML sintético dado que el mecanismo
— extracción selectiva por xpath explícito, nunca "iterar y guardar todo lo que
aparezca" — hace estructuralmente imposible que datos no mapeados lleguen a
persistirse).
