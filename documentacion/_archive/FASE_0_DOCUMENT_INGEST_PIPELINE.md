# FASE 0: Document Ingest Pipeline Universal - Resumen de Implementación

**Fecha:** 2026-02-10  
**Estado:** ✅ Estructura Base Completada  
**Objetivo:** Evolucionar servicios XML hacia pipeline universal de documentos (XML, PDF, XLS/XLSX, CSV, TXT)

## 📋 Componentes Implementados

### 1. Estructura de Directorios

```
apps/services/
├── document_parser/          # Low-level parsing/normalization
│   ├── __init__.py
│   ├── interfaces.py         # IParser, IDetector, INormalizer
│   ├── dto.py                # DTO unificado JSON
│   ├── normalizers.py        # Normalización UTF-8, limpieza
│   └── parsers/              # Parsers específicos (pendiente migración)
│       └── (futuro: xml_ubl_invoice.py, pdf_invoice.py, etc.)
│
└── document_ingest/          # Orchestration/routing/validation
    ├── __init__.py
    ├── registry.py           # DocumentRegistry (Strategy Pattern)
    ├── ingest_service.py     # Servicio principal de ingesta
    └── validators.py         # Validación de integridad DTO
```

### 2. Interfaces Base (Extensibilidad)

**`apps/services/document_parser/interfaces.py`:**

- **`IParser`**: Interfaz base para todos los parsers
  - `document_type`: Tipo canónico del documento
  - `supported_formats`: Formatos soportados (ej: ["xml", "pdf"])
  - `can_parse()`: Detecta si puede procesar el documento
  - `parse()`: Parsea a DTO JSON unificado

- **`IDetector`**: Interfaz para detectores de tipo
  - `detect()`: Detecta tipo por extensión, magic bytes, contenido

- **`INormalizer`**: Interfaz para normalizadores
  - `normalize()`: Normaliza codificación, limpia contenido

### 3. DTO Unificado JSON

**`apps/services/document_parser/dto.py`:**

Estructura estándar para todos los formatos:

```python
{
    "document_type": "invoice.ubl21",
    "numero": "FAC-123",
    "identificadores": {
        "cufe": "...",
        "uuid": "...",
        "numero": "..."
    },
    "fecha_emision": "2026-02-10T10:00:00Z",
    "emisor": {
        "nit": "900123456",
        "razon_social": "...",
        "direccion": "...",
        "email": "...",
        "telefono": "..."
    },
    "receptor": {...},
    "totales": {
        "moneda": "COP",
        "subtotal": "100000.00",
        "impuestos": "19000.00",
        "total": "119000.00"
    },
    "referencia": {...},  # Solo para Notas Crédito
    "motivo": "...",      # Solo para Notas Crédito
    "formato_origen": "xml",
    "parser_usado": "XMLUBLInvoiceParser"
}
```

### 4. Normalizadores

**`apps/services/document_parser/normalizers.py`:**

- `normalize_encoding()`: UTF-8 con detección automática
- `remove_binary_embeds()`: Eliminación de binarios incrustados
- `sanitize_text()`: Limpieza de caracteres ilegales, trimming
- `normalize_nit()`: Normalización de NITs
- `normalize_currency()`: Normalización de códigos de moneda

### 5. Registry (Strategy Pattern)

**`apps/services/document_ingest/registry.py`:**

- **`DocumentRegistry`**: Centraliza detección y routing de parsers
  - Auto-registro de parsers al importar
  - Detección automática de tipo de documento
  - Extensible: nuevos tipos sin tocar orquestación

### 6. Servicio de Ingesta Principal

**`apps/services/document_ingest/ingest_service.py`:**

- **`ingest_document()`**: Función principal de ingesta
  - Normalización de contenido
  - Detección automática de tipo
  - Parsing a DTO unificado
  - Validación de integridad
  - Preview mode (sin persistir)
  - Persistencia delegada a services de dominio
  - Logging estructurado

**Contrato de respuesta:**

```python
{
    "document_type": str,
    "dto": {...},
    "persisted": bool,
    "id": int (si persisted=True),
    "error": str (si hay error),
    "message": str (si hay error),
}
```

### 7. Validadores

**`apps/services/document_ingest/validators.py`:**

- **`validate_document_dto()`**: Valida integridad y campos obligatorios
- **`validate_invoice_dto()`**: Alias para facturas
- **`validate_credit_note_dto()`**: Alias para notas crédito

**Campos obligatorios validados:**
- `numero`, `identificadores`, `fecha_emision`
- `emisor.nit`, `emisor.razon_social`
- `receptor.nit`, `receptor.razon_social`
- `totales.moneda`, `totales.total`
- `referencia` (solo para Notas Crédito)

## 🔄 Compatibilidad con Sistema Existente

### Mantenimiento de Backward Compatibility

- El sistema XML existente (`apps/services/xml_ingest`, `apps/services/xml_parser`) sigue funcionando
- La nueva estructura es paralela y no rompe funcionalidad existente
- Migración gradual: parsers XML se migrarán en fases siguientes

### Integración con Services de Dominio

El servicio de ingesta delega persistencia a:
- `apps/tenant/facturas/services.guardar_factura_desde_dto()`
- `apps/tenant/facturas/services.guardar_nota_credito_desde_dto()`

Mantiene:
- Idempotencia por CUFE/CUDE
- Transaccionalidad (`@transaction.atomic`)
- Validaciones de negocio (1:1, existencia de factura, etc.)

## 📝 Próximos Pasos (Pendientes)

### FASE 0 - Continuación

1. **Migrar Parsers XML** (`fase0-4`):
   - Crear `apps/services/document_parser/parsers/xml_ubl_invoice.py`
   - Crear `apps/services/document_parser/parsers/xml_ubl_credit_note.py`
   - Adaptar parsers existentes a nueva interfaz `IParser`

2. **Implementar Parsers Adicionales** (`fase0-4`):
   - PDF Parser (para facturas en PDF)
   - Excel Parser (XLS/XLSX)
   - CSV Parser
   - TXT Parser

3. **Logging Estructurado** (`fase0-9`):
   - Completar logging en todos los puntos críticos
   - Asegurar que errores nunca expongan trazas internas

4. **Tests de Integración** (`fase0-10`):
   - Tests para cada parser
   - Tests de validación
   - Tests de normalización
   - Tests end-to-end del pipeline

## ✅ Reglas Arquitectónicas Cumplidas

- ✅ **API-First con DRF (JSON-only)**: DTO unificado JSON
- ✅ **Service Layer Pattern**: Separación clara de responsabilidades
- ✅ **SSoT**: Pipeline es única fuente de verdad para parsing
- ✅ **Multitenant**: Persistencia bajo tenant_context
- ✅ **Inmutabilidad**: Delegada a services de dominio
- ✅ **Seguridad y limpieza**: Normalizadores implementados
- ✅ **Idempotencia**: Delegada a services de dominio
- ✅ **Extensibilidad**: Registry permite agregar tipos sin tocar orquestación
- ✅ **Observabilidad**: Logging estructurado implementado

## 🔗 Referencias

- **Interfaces**: `apps/services/document_parser/interfaces.py`
- **DTO**: `apps/services/document_parser/dto.py`
- **Registry**: `apps/services/document_ingest/registry.py`
- **Ingest Service**: `apps/services/document_ingest/ingest_service.py`
- **Validators**: `apps/services/document_ingest/validators.py`
- **Normalizers**: `apps/services/document_parser/normalizers.py`
