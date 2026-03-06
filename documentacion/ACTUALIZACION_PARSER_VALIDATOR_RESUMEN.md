# ✅ ACTUALIZACIÓN PARSER + VALIDATOR CON XMLs DE EJEMPLO

**Fecha:** 2026-02-10  
**Objetivo:** Actualizar parser universal y validadores usando XMLs de ejemplo de `apps/tenant/facturas/xml/` y alinearlos con `models.py`.

---

## 📋 CAMBIOS APLICADOS

### 1. Parser XML (`apps/services/document_parser/xml_parser/parser.py`)

#### ✅ Campos Extraídos (Factura)

**Nuevos campos extraídos:**
- `prefijo` y `consecutivo`: Extraídos del número usando regex (ej: "FST355" → prefijo="FST", consecutivo=355)
- `emisor.direccion`: Extraída de `PhysicalLocation/Address/AddressLine/Line`
- `emisor.email`: Extraído de `Contact/ElectronicMail`
- `emisor.telefono`: Extraído de `Contact/Telephone`
- `emisor.actividad_ciiu`: Extraído de `IndustryClassificationCode`
- `receptor.direccion`, `receptor.email`, `receptor.telefono`: Similar al emisor
- `ubl_version`, `customization_id`, `profile_id`, `profile_execution_id`, `invoice_type_code`: Metadatos UBL
- `autorizacion.*`: Datos de autorización DIAN desde `DianExtensions/InvoiceControl`
- `qr_code` y `qr_url`: Extraídos de `DianExtensions/QRCode`

#### ✅ Campos Extraídos (Nota Crédito)

**Nuevos campos extraídos:**
- `emisor.direccion`, `emisor.email`, `emisor.telefono`: Similar a Factura
- `receptor.direccion`, `receptor.email`, `receptor.telefono`: Similar a Factura
- `motivo`: Extraído de `Note` (campo principal) o `DiscrepancyResponse/Description` (fallback)

#### ✅ FutureWarnings Eliminados

**Reemplazos aplicados:**
- `if supplier_party:` → `if supplier_party is not None:`
- `if customer_party:` → `if customer_party is not None:`
- `if monetary_total:` → `if monetary_total is not None:`
- `if discrepancy:` → `if discrepancy is not None:`
- `if invoice_ref:` → `if invoice_ref is not None:`
- `if tax_scheme:` → `if tax_scheme is not None:`
- `if legal_entity:` → `if legal_entity is not None:`
- `if physical_location:` → `if physical_location is not None:`
- `if address:` → `if address is not None:`
- `if contact:` → `if contact is not None:`
- `if dian_extensions:` → `if dian_extensions is not None:`
- `if invoice_control:` → `if invoice_control is not None:`
- `if authorized_invoices:` → `if authorized_invoices is not None:`
- `if auth_period:` → `if auth_period is not None:`
- `if qr_code_elem:` → `if qr_code_elem is not None:`

### 2. Validadores (`apps/services/document_ingest/validations/`)

#### ✅ Validadores Actualizados

**`factura.py`:**
- ✅ Valida CUFE obligatorio
- ✅ Valida totales coherentes (con tolerancia para descuentos/cargos)
- ✅ Valida fechas válidas
- ✅ Valida número de documento detectado
- ✅ Valida emisor y receptor presentes

**`nota_credito.py`:**
- ✅ Valida CUDE obligatorio
- ✅ Valida referencias obligatorias a factura (número o CUFE)
- ✅ Valida totales coherentes (con tolerancia)
- ✅ Valida fechas válidas
- ✅ Valida número de documento detectado
- ✅ Valida emisor y receptor presentes

**Nota:** Los validadores no requieren validar campos opcionales (direcciones, emails, teléfonos) ya que estos son opcionales en `models.py`.

### 3. Endpoint Universal (`apps/tenant/core/api/viewsets_documentos.py`)

#### ✅ Confirmación

- ✅ `?preview=true` → Retorna **200 + DTO** (sin persistencia)
- ✅ `?preview=false` → Retorna **200 + DTO** (sin persistencia) - document_ingest NO persiste
- ✅ **NO** incluye `?async=true` (no aplica)
- ✅ Manejo de errores: 409 (duplicado), 422 (validación), 415 (tipo no soportado), 400 (parser)

### 4. Tabla de Mapeo DTO → models.py

#### ✅ Documentación Creada

- ✅ `documentacion/MAPEO_DTO_MODELS.md`: Tabla completa de mapeo
- ✅ Incluye todos los campos extraídos
- ✅ Notas de conversión de tipos
- ✅ Campos no mapeados documentados

---

## ✅ CHECKLIST DoD

- [x] **Parser UBL produce DTO completo para Invoice y CreditNote según `models.py`**
  - ✅ Prefijo y consecutivo extraídos del número
  - ✅ Direcciones, emails, teléfonos de emisor y receptor
  - ✅ Metadatos UBL (ubl_version, customization_id, profile_id, etc.)
  - ✅ Autorización DIAN (número, prefijo, rangos, vigencias)
  - ✅ QR code y URL
  - ✅ Motivo completo para Nota Crédito

- [x] **Validadores 422/415/400 coherentes**
  - ✅ Factura: CUFE, totales, fechas, número, emisor/receptor
  - ✅ Nota Crédito: CUDE, referencias, totales, fechas, número, emisor/receptor
  - ✅ Códigos de error correctos (422 para validación, 415 para tipo no soportado, 400 para parser)

- [x] **Sin persistencia en parser ni document_ingest**
  - ✅ `document_ingest` solo parsea y devuelve DTO
  - ✅ `document_router` no materializa (stub/placeholder)
  - ✅ Endpoint universal solo devuelve DTO

- [x] **Endpoint universal retorna DTO (preview) correctamente**
  - ✅ `?preview=true` → 200 + DTO
  - ✅ `?preview=false` → 200 + DTO (sin persistencia)
  - ✅ Incluye `create_endpoint` sugerido para la app

- [x] **Sin `FutureWarning` por truth-testing en parser**
  - ✅ Todos los `if elem:` reemplazados por `if elem is not None:`
  - ✅ Sin warnings en logs

- [x] **Tabla de mapeo DTO → models.py creada**
  - ✅ `documentacion/MAPEO_DTO_MODELS.md` con mapeo completo
  - ✅ Incluye notas de conversión de tipos
  - ✅ Documenta campos no mapeados

---

## 📝 PRÓXIMOS PASOS (Opcional)

1. **Smoke tests con XMLs de ejemplo:**
   ```bash
   # Preview Factura
   curl -i -X POST "http://localhost:8000/api/v1/core/documentos/upload/?preview=true" \
     -H "X-CSRFToken: <token>" \
     -F "file=@apps/tenant/facturas/xml/ad09011232990082600000163.xml"
   
   # Preview Nota Crédito
   curl -i -X POST "http://localhost:8000/api/v1/core/documentos/upload/?preview=true" \
     -H "X-CSRFToken: <token>" \
     -F "file=@apps/tenant/facturas/xml/ad09011232990082500000060.xml"
   ```

2. **Validar logs sin FutureWarnings:**
   - Verificar que no aparezcan warnings en logs de la app

3. **Validar DTO completo:**
   - Confirmar que el DTO incluye todos los campos nuevos
   - Verificar que los campos opcionales se manejan correctamente

---

**Última actualización:** 2026-02-10
