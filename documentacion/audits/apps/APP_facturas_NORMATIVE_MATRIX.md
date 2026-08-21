# APP_facturas_NORMATIVE_MATRIX — Matriz normativa colombiana

Parte de `documentacion/audits/apps/APP_facturas_AUDIT.md` (FASE M).
**Resuelve el hallazgo pendiente de `ventas`** (app 9/16): la
correccion tecnica de CUFE/UBL2.1/XAdES delegada a
`apps/tenant/facturas/services/dian/*`.

## Pipeline DIAN real (`services/dian/`)

| Archivo | Responsabilidad | Verificacion |
|---|---|---|
| `cufe.py` | Calculo del CUFE, SHA-384 sobre 14 campos fiscales concatenados | **Verificado linea por linea.** Cita explicita "Anexo Tecnico FE DIAN v1.9 seccion 5.4.3" en docstring. Formula: `SHA-384(NumFac+FecFac+HorFac+ValFac+"01"+ValImp1(IVA)+"04"+ValImp2(INC)+"03"+ValImp3(ICA)+ValTot+NitOFE+NumAdq+ClTecn+TipAmb)`. Orden de campos, codigos de impuesto (01=IVA, 04=INC, 03=ICA) y longitud de salida (96 hex = SHA-384/384bits) consistentes con la estructura publica conocida del algoritmo CUFE DIAN. Default seguro: `TipAmb` cae a `"2"` (habilitacion/pruebas) si no esta configurado explicitamente -- nunca asume produccion por defecto. |
| `ubl21_builder.py` | Construccion del XML `Invoice` UBL 2.1 (429 lineas) | Revisado a nivel estructural (no linea por linea por alcance de tiempo) -- construye el documento UBL que luego firma `xades_signer.py` |
| `xades_signer.py` | Firma XAdES-EPES (282 lineas) | Cita "Anexo Tecnico FE DIAN v1.9 seccion 5.5" y la politica de firma oficial (URL DIAN). Documenta su propio comportamiento defensivo: si `settings.DIAN_CERT_P12` esta vacio, retorna el XML SIN firmar (modo "borrador"/desarrollo) -- no falla silenciosamente ni firma con una clave falsa |
| `attached_document.py` | Envuelve el Invoice firmado en `AttachedDocument` (187 lineas) | Revisado a nivel estructural |

## HALLAZGO PRINCIPAL (P1): la transmision real a DIAN nunca ocurre

**Verificado con evidencia exhaustiva:** ningun archivo en
`apps/tenant/facturas` (ni en `services/dian/`, ni en
`business_service.py`, ni en tasks/Celery) contiene una llamada HTTP/
SOAP real al webservice de la DIAN -- grep repo-wide de
`requests.post`/`requests.Session`/`zeep`/`SOAP`/`wsdl` en toda la app
no encuentra ningun cliente HTTP/SOAP hacia `dian.gov.co` (las unicas
coincidencias de "dian.gov.co" son URLs en docstrings/comentarios y la
URL del QR publico, no llamadas de red reales).

El pipeline completo (CUFE -> UBL XML -> firma XAdES -> AttachedDocument)
**se detiene ahi** -- nunca se envia el documento firmado a la DIAN, y
nunca se procesa una respuesta real. Confirmado con el campo
`FacturaAnexos.application_response_xml` (`models.py:654`, "XML de
respuesta de la DIAN"): grep de sus escrituras en todo el repo
muestra que **solo se puebla en dos lugares, ninguno es una respuesta
real de DIAN**:
1. `management/commands/backfill_facturas_anexos.py` -- comando de
   backfill/migracion de datos historicos, no parte del flujo en vivo.
2. `utils/ubl_parser.py:1231` -- se fija a `None` con el comentario
   "Se puede poblar si se detecta en el XML" (solo si el XML
   IMPORTADO ya trae la respuesta incluida, es decir, para facturas
   de COMPRA recibidas ya procesadas por el proveedor -- no para
   facturas de VENTA emitidas por este tenant).

**Este es el mismo patron arquitectonico que DEUDA-11 en `empleados`**
(nomina electronica DIAN: infraestructura de datos completa y
correcta, transmision XML real no implementada) -- pero aqui aplica a
**facturas de venta regulares**, el caso de uso central de facturacion
electronica del sistema, no a un modulo secundario (nomina). Mayor
criticidad potencial si hay tenants reales que dependen de la emision
electronica real ante la DIAN.

## Matriz

| # | Obligacion | Sujeto obligado | Supuesto de hecho | Norma | Evidencia | Aplicabilidad |
|---|---|---|---|---|---|---|
| 1 | Calculo correcto del CUFE | Empresa (emisor electronico) | Toda factura de venta facturada | Anexo Tecnico FE DIAN v1.9 §5.4.3 | `cufe.py` (verificado) | **OBLIGATORIO -- implementado correctamente** segun la estructura publica conocida del algoritmo |
| 2 | Generacion de XML UBL 2.1 valido | Empresa (emisor) | Igual a #1 | Estandar UBL 2.1 + Anexo Tecnico DIAN | `ubl21_builder.py` (revision estructural) | **OBLIGATORIO** -- implementado, no verificado exhaustivamente campo por campo en este pase |
| 3 | Firma XAdES-EPES del documento | Empresa (emisor) | Igual a #1, si hay certificado configurado | Anexo Tecnico FE DIAN v1.9 §5.5 + politica de firma DIAN v2 | `xades_signer.py` (revision estructural + comportamiento defensivo verificado) | **OBLIGATORIO** -- implementado con fallback seguro (sin firmar) si no hay certificado |
| 4 | **Transmision del documento firmado a la DIAN y procesamiento de la respuesta oficial (Track ID / validacion)** | Empresa (emisor electronico obligado) | Toda factura que deba tener validez legal como factura electronica ante la DIAN | Resolucion DIAN de facturacion electronica (transmision y validacion) | **NO ENCONTRADO EN NINGUN ARCHIVO** -- confirmado con grep exhaustivo | **GAP CONFIRMADO (P1)** -- sin esto, las facturas generadas por el sistema NO tienen validez legal como factura electronica ante la DIAN (el CUFE/XML/firma se calculan pero nunca se radican). Prioridad real depende de si hay tenants en produccion emitiendo facturas de venta que requieran validez DIAN -- fuera del alcance de esta auditoria de codigo confirmar cuantos |

## Deferred

| # | Item | Prioridad |
|---|---|---|
| 1 | Transmision real del documento firmado al webservice DIAN + procesamiento de `ApplicationResponse` -- no implementada en ningun punto del pipeline | **P1** (mismo patron que DEUDA-11 de `empleados`, pero para facturas de venta, el caso de uso central) |
| 2 | `ubl21_builder.py`/`attached_document.py` no se revisaron campo por campo (429 + 187 lineas) -- solo verificacion estructural por alcance de tiempo en esta auditoria de 16 apps | P3 (revision profunda pendiente si se requiere certificacion formal DIAN) |
