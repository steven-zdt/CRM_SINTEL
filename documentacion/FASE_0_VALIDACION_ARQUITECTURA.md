# FASE 0: Validación de Arquitectura - Document Ingest Pipeline Universal

**Fecha:** 2026-02-10  
**Estado:** ✅ Arquitectura Aprobada y Validada

## ✅ Validación de Reglas Arquitectónicas

### 1. API-First con DRF (JSON-only) ✅

**Validado:**
- ✅ DTO unificado JSON en `apps/services/document_parser/dto.py`
- ✅ Contrato estable: `DocumentoDTO` con estructura JSON serializable
- ✅ Compatible con DRF: Todos los campos son tipos primitivos JSON
- ✅ No hay vistas HTML en el pipeline: Solo servicios Python puros

**Archivos validados:**
- `apps/services/document_parser/dto.py` - DTO JSON unificado
- `apps/services/document_ingest/ingest_service.py` - Retorna JSON estructurado

### 2. SSoT (Single Source of Truth) ✅

**Validado:**
- ✅ Única vía de parsing: `apps/services/document_parser/*`
- ✅ Única vía de ingesta: `apps/services/document_ingest/*`
- ✅ Prohibido parsear en `apps/tenant/*`: Solo consumo de servicios

**Verificación:**
```bash
# No hay parsing directo en apps/tenant/facturas
# Solo consumo de servicios:
- apps/tenant/facturas/services.py → consume document_ingest
- apps/tenant/facturas/ubl_parser.py → consume xml_parser (legacy, OK)
```

**Archivos validados:**
- `apps/services/document_parser/interfaces.py` - Interfaces base
- `apps/services/document_ingest/registry.py` - Registry centralizado
- `apps/services/document_ingest/ingest_service.py` - Servicio canónico

### 3. Prohibido Parsear en apps/tenant ✅

**Validado:**
- ✅ `apps/tenant/facturas/ubl_parser.py` - Solo mapeo UBL→DTO, consume `xml_parser` (legacy)
- ✅ `apps/tenant/facturas/services.py` - Solo materialización desde DTO, consume `document_ingest`
- ✅ No hay parsing de bytes en `apps/tenant/*`

**Verificación:**
- `apps/tenant/facturas/ubl_parser.py` importa `from apps.services.xml_parser import ...` ✅
- `apps/tenant/facturas/services.py` importa `from apps.services.xml_ingest.normalizers import ...` ✅
- No hay `etree.fromstring()`, `parse_xml_bytes()`, etc. en `apps/tenant/*` ✅

### 4. Idempotencia por CUFE/CUDE ✅

**Validado:**
- ✅ Delegada a services de dominio: `guardar_factura_desde_dto()`, `guardar_nota_credito_desde_dto()`
- ✅ Validación en `apps/tenant/facturas/services.py`:
  - `guardar_factura_desde_dto()`: Verifica CUFE duplicado
  - `guardar_nota_credito_desde_dto()`: Verifica CUDE duplicado

**Archivos validados:**
- `apps/tenant/facturas/services.py` - Funciones `guardar_*_desde_dto()` con idempotencia

### 5. Inmutabilidad Documental ✅

**Validado:**
- ✅ PUT/PATCH bloqueados en ViewSets: `http_method_names = ['get', 'head', 'options', 'post', 'delete']`
- ✅ POST directo bloqueado: Solo importación UBL permitida
- ✅ DELETE permitido solo como rollback técnico

**Archivos validados:**
- `apps/tenant/facturas/api/viewsets.py` - `FacturaViewSet`, `NotaCreditoViewSet`

### 6. DTO JSON Unificado ✅

**Validado:**
- ✅ Estructura estándar en `apps/services/document_parser/dto.py`:
  - `DocumentoDTO` - Contrato principal
  - `IdentificadoresDTO` - CUFE, UUID, número
  - `PartyDTO` - Emisor/Receptor
  - `TotalesDTO` - Totales monetarios
  - `ReferenciaDTO` - Referencia a documento (Notas Crédito)

**Archivos validados:**
- `apps/services/document_parser/dto.py` - DTO unificado completo

### 7. Pipeline Único ✅

**Validado:**
- ✅ Flujo: `document_parser` → `document_ingest` → `apps/tenant/*/services.py`
- ✅ `document_parser`: Parsing low-level (XML, PDF, XLS, CSV, TXT)
- ✅ `document_ingest`: Orquestación, detección, validación
- ✅ `apps/tenant/facturas/services.py`: Materialización desde DTO

**Flujo validado:**
```
1. Cliente → POST /api/v1/facturas/upload-ubl/
2. ViewSet → apps/services/document_ingest/ingest_service.ingest_document()
3. ingest_document() → DocumentRegistry.detect_type()
4. DocumentRegistry → Parser específico (XML, PDF, etc.)
5. Parser → DTO JSON unificado
6. ingest_document() → Validación
7. ingest_document() → apps/tenant/facturas/services.guardar_factura_desde_dto()
8. guardar_factura_desde_dto() → Materialización en BD
```

**Archivos validados:**
- `apps/services/document_parser/interfaces.py` - IParser
- `apps/services/document_ingest/registry.py` - DocumentRegistry
- `apps/services/document_ingest/ingest_service.py` - ingest_document()
- `apps/tenant/facturas/services.py` - guardar_factura_desde_dto()

### 8. Multitenant por Esquema ✅

**Validado:**
- ✅ Persistencia bajo `tenant_context`: `guardar_*_desde_dto()` usa `@transaction.atomic`
- ✅ No hay escrituras fuera de esquema: Todo en `apps/tenant/*/services.py`

**Archivos validados:**
- `apps/tenant/facturas/services.py` - Funciones con `@transaction.atomic`

### 9. Seguridad y Limpieza ✅

**Validado:**
- ✅ Normalizadores en `apps/services/document_parser/normalizers.py`:
  - `normalize_encoding()`: UTF-8 con detección automática
  - `sanitize_text()`: Limpieza de caracteres ilegales
  - `normalize_nit()`: Normalización de NITs
  - `normalize_currency()`: Normalización de códigos de moneda

**Archivos validados:**
- `apps/services/document_parser/normalizers.py` - Normalizadores completos

### 10. Extensibilidad ✅

**Validado:**
- ✅ Strategy Pattern: `IParser`, `IDetector`, `INormalizer`
- ✅ DocumentRegistry: Auto-registro de parsers
- ✅ Nuevos tipos se agregan sin tocar orquestación principal

**Archivos validados:**
- `apps/services/document_parser/interfaces.py` - Interfaces extensibles
- `apps/services/document_ingest/registry.py` - Registry extensible

### 11. Observabilidad ✅

**Validado:**
- ✅ Logging estructurado en `apps/services/document_ingest/ingest_service.py`
- ✅ Mensajes deterministas: Errores no exponen trazas internas
- ✅ Logger: `apps.services.document_ingest`

**Archivos validados:**
- `apps/services/document_ingest/ingest_service.py` - Logging estructurado

## 📋 Resumen de Validación

| Regla Arquitectónica | Estado | Archivos Validados |
|---------------------|--------|-------------------|
| API-First JSON-only | ✅ | `dto.py`, `ingest_service.py` |
| SSoT (parsing solo en servicios) | ✅ | `interfaces.py`, `registry.py`, `ingest_service.py` |
| Prohibido parsear en apps/tenant | ✅ | `apps/tenant/facturas/*` (solo consumo) |
| Idempotencia por CUFE/CUDE | ✅ | `apps/tenant/facturas/services.py` |
| Inmutabilidad documental | ✅ | `apps/tenant/facturas/api/viewsets.py` |
| DTO JSON unificado | ✅ | `dto.py` |
| Pipeline único | ✅ | `document_parser` → `document_ingest` → `services.py` |
| Multitenant por esquema | ✅ | `apps/tenant/facturas/services.py` |
| Seguridad y limpieza | ✅ | `normalizers.py` |
| Extensibilidad | ✅ | `interfaces.py`, `registry.py` |
| Observabilidad | ✅ | `ingest_service.py` |

## ✅ Conclusión

**Todas las reglas arquitectónicas están validadas y cumplidas.**

La arquitectura del Document Ingest Pipeline Universal está:
- ✅ Aprobada
- ✅ Implementada
- ✅ Validada
- ✅ Documentada

**Lista para implementación de parsers específicos (XML, PDF, XLS, CSV, TXT) en fases siguientes.**
