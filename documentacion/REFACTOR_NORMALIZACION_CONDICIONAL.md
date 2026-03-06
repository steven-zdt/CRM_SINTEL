# 🔧 REFACTOR — Normalización Condicional por Tipo de Documento

**Fecha:** 2026-02-10  
**Problema:** La normalización se aplicaba a todos los tipos de documentos, incluyendo XML

---

## 📋 ANÁLISIS DEL PROBLEMA

### Comportamiento Anterior:
- `normalize_encoding()` se aplicaba a **TODOS** los documentos (XML, PDF, Excel, CSV, TXT)
- El parser XML también aplicaba `normalize_encoding()` internamente
- Esto podía causar problemas con XML que ya tiene encoding correcto

### Requerimiento:
- **Normalización solo para PDF y Excel**
- **XML, CSV, TXT**: No aplicar normalización de encoding (los parsers manejan su propio encoding)

---

## ✅ CORRECCIÓN APLICADA

### 1. `apps/services/document_ingest/ingest_service.py`

**Antes:**
```python
# 3. Normalizar contenido (UTF-8, limpieza)
normalized_content = normalize_encoding(content)
route_result = route(normalized_content, filename, mime_type)
```

**Después:**
```python
# 3. Detectar tipo de documento para decidir si normalizar
# ⚠️ REFACTOR: Normalización solo para PDF y Excel, NO para XML
detection_result = detect_document_type(content, filename, mime_type)
detected_media_type = detection_result.get("media_type", "")

# Solo normalizar si es PDF o Excel
should_normalize = detected_media_type in ("pdf", "excel")

if should_normalize:
    normalized_content = normalize_encoding(content)
else:
    # Para XML/CSV/TXT, usar contenido original sin normalizar
    normalized_content = content
```

**Cambios:**
- ✅ Detecta tipo de documento ANTES de normalizar
- ✅ Solo normaliza si `media_type` es "pdf" o "excel"
- ✅ Para XML/CSV/TXT, usa contenido original (sin normalizar encoding)

### 2. `apps/services/document_parser/xml_parser/parser.py`

**Antes:**
```python
# Normalizar encoding
normalized_bytes = normalize_encoding(file_bytes)
xml_root = parse_xml_bytes(normalized_bytes)
```

**Después:**
```python
# ⚠️ REFACTOR: NO normalizar encoding para XML - lxml maneja encoding automáticamente
# La normalización solo se aplica a PDF y Excel en ingest_service.py
# Parsear XML directamente (lxml detecta encoding desde declaración <?xml encoding="...">)
xml_root = parse_xml_bytes(file_bytes)
```

**Cambios:**
- ✅ Eliminado `normalize_encoding()` del parser XML
- ✅ `lxml` maneja encoding automáticamente desde la declaración XML
- ✅ Mantiene `sanitize_text()`, `normalize_nit()`, `normalize_currency()`, `normalize_numeric_to_decimal_string()` (normalizaciones de datos, no de encoding)

---

## 📊 TIPOS DE NORMALIZACIÓN

### Normalización de Encoding (SOLO PDF/Excel):
- `normalize_encoding()`: Convierte a UTF-8
- Se aplica en `ingest_service.py` antes del routing
- **NO se aplica a XML/CSV/TXT**

### Normalización de Datos (Todos los tipos):
- `sanitize_text()`: Limpia espacios, caracteres de control
- `normalize_nit()`: Normaliza formato de NIT
- `normalize_currency()`: Normaliza código de moneda
- `normalize_numeric_to_decimal_string()`: Convierte números a string decimal
- **Se aplica en parsers específicos según necesidad**

---

## ✅ VALIDACIÓN

### XML:
- ✅ No se aplica `normalize_encoding()` en `ingest_service.py`
- ✅ No se aplica `normalize_encoding()` en `xml_parser/parser.py`
- ✅ `lxml` maneja encoding desde declaración XML
- ✅ Se mantienen normalizaciones de datos (`sanitize_text`, `normalize_nit`, etc.)

### PDF:
- ✅ Se aplica `normalize_encoding()` en `ingest_service.py`
- ✅ Parser PDF recibe contenido normalizado

### Excel:
- ✅ Se aplica `normalize_encoding()` en `ingest_service.py`
- ✅ Parser Excel recibe contenido normalizado

---

**Última actualización:** 2026-02-10
