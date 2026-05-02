# ✅ REVERSIÓN — Eliminación de Excepciones de Normalización

**Fecha:** 2026-02-10  
**Objetivo:** Forzar normalización SIEMPRE para TODOS los tipos de archivo (XML, CSV, XLS/XLSX, TXT, PDF) antes de parsing/validación.

---

## 📋 CAMBIOS APLICADOS

### 1. Función Unificada de Normalización (`apps/services/document_parser/normalizers.py`)

#### ✅ Nueva función `normalize_content()`

**Función creada:**
```python
def normalize_content(
    content: bytes,
    filename: Optional[str] = None,
    mime_type: Optional[str] = None
) -> Dict[str, Any]
```

**Características:**
- ✅ Detecta tipo de documento (XML, CSV, Excel, TXT, PDF)
- ✅ Normaliza según tipo:
  - **XML**: UTF-8, elimina BOM, preserva estructura
  - **CSV**: UTF-8, detecta delimitador, normaliza newlines (CRLF→LF)
  - **Excel**: Preserva binario, normaliza encoding de metadatos
  - **TXT**: UTF-8, LF, trimming, whitespace normalizado
  - **PDF**: Preserva binario (parser PDF maneja extracción)
- ✅ Retorna dict con `media_type`, `normalized` (bytes|str|DataFrame), `meta` (cleanups aplicados)
- ✅ **Nunca** lanza excepción por casos tratables; solo 415 si tipo no reconocido

#### ✅ Nueva función `normalize_xml()`

**Función creada:**
```python
def normalize_xml(xml_bytes: bytes) -> bytes
```

**Características:**
- ✅ Elimina BOM (UTF-8, UTF-16)
- ✅ Normaliza encoding a UTF-8
- ✅ Preserva estructura XML (no elimina firmas XAdES automáticamente)

### 2. Enforcer en `ingest_service.py`

#### ✅ Normalización SIEMPRE aplicada

**Antes:**
```python
# Solo normalizar si es PDF o Excel
should_normalize = detected_media_type in ("pdf", "excel")
if should_normalize:
    normalized_content = normalize_encoding(content)
else:
    normalized_content = content  # ⚠️ BYPASS
```

**Después:**
```python
# ⚠️ REVERSIÓN: Normalización SIEMPRE aplicada a TODOS los tipos
normalization_result = normalize_content(
    content=content,
    filename=filename,
    mime_type=mime_type
)
normalized_content = normalization_result.get("normalized")
media_type = normalization_result.get("media_type")
```

**Características:**
- ✅ **NO hay bypass**: Todos los tipos pasan por normalización
- ✅ **NO hay short-circuit**: No hay rutas alternativas
- ✅ **NO hay raw passthrough**: El router recibe contenido normalizado
- ✅ Manejo de errores: 415 para tipo no reconocido, 400 para errores de normalización

### 3. Router Actualizado (`apps/services/document_ingest/router.py`)

#### ✅ Acepta contenido normalizado (bytes o str)

**Cambios:**
- ✅ Firma actualizada: `route(file_bytes: Union[bytes, str], ..., media_type: Optional[str] = None)`
- ✅ Usa `media_type` del normalizer si está disponible (evita detección duplicada)
- ✅ Convierte tipos según media_type:
  - XML/PDF/Excel: bytes
  - CSV/TXT: str (ya viene normalizado como string)

### 4. Parsers Actualizados

#### ✅ CSV Parser (`apps/services/document_parser/csv_parser/parser.py`)

**Cambios:**
- ✅ Acepta `bytes` o `str` (el normalizer entrega string para CSV)
- ✅ Convierte a bytes si es necesario para `normalize_csv_to_dataframe`

#### ✅ TXT Parser (`apps/services/document_parser/txt_parser/parser.py`)

**Cambios:**
- ✅ Acepta `bytes` o `str` (el normalizer entrega string para TXT)
- ✅ Usa string directamente si viene del normalizer

#### ✅ XML Parser (`apps/services/document_parser/xml_parser/parser.py`)

**Estado:**
- ✅ Ya recibe bytes UTF-8 normalizados
- ✅ `parse_xml_bytes()` maneja encoding automáticamente (lxml)
- ✅ FutureWarnings eliminados (`if elem is not None`)

### 5. Endpoint Universal (`apps/tenant/core/api/viewsets_documentos.py`)

#### ✅ Confirmación

- ✅ **NO** salta normalización (la hace `ingest_service`)
- ✅ **NO** usa `?async=true` (solo `?preview=true|false`)
- ✅ Retorna DTO sin persistir (siempre)

### 6. JavaScript (`apps/tenant/core/static/core/js/facturas.ui.js`)

#### ✅ Confirmación

- ✅ **NO** usa `?async=true`
- ✅ Usa `?preview=true` para recibir DTO
- ✅ Maneja errores 409/422/415/400 con mensajes canónicos

---

## 🗑️ BYPASSES/FLAGS ELIMINADOS

### Flags/Rutas Removidos:

1. **`should_normalize`** (condicional en `ingest_service.py`):
   - ❌ **ELIMINADO**: Ya no hay condición que salte normalización
   - ✅ **REEMPLAZADO**: Normalización SIEMPRE aplicada

2. **`document_ingest_skip_normalization`** (log):
   - ❌ **ELIMINADO**: Ya no se registra este evento
   - ✅ **REEMPLAZADO**: `document_ingest_normalization_ok` siempre

3. **`normalized_content = content`** (fallback):
   - ❌ **ELIMINADO**: Ya no hay fallback que use contenido original
   - ✅ **REEMPLAZADO**: Siempre se normaliza o se retorna error

4. **Detección duplicada en router**:
   - ❌ **OPTIMIZADO**: Router usa `media_type` del normalizer si está disponible
   - ✅ **MEJORADO**: Evita detección duplicada

---

## ✅ CHECKLIST DoD

- [x] **No existen bypass de normalización en el repo**
  - ✅ Eliminado `should_normalize` condicional
  - ✅ Eliminado `skip_normalization` log
  - ✅ Eliminado fallback a contenido original

- [x] **`ingest_service` SIEMPRE normaliza antes de parsear**
  - ✅ `normalize_content()` llamado SIEMPRE
  - ✅ No hay short-circuit ni raw passthrough
  - ✅ Errores de normalización retornan 415/400

- [x] **Parsers consumen EXCLUSIVAMENTE contenido normalizado**
  - ✅ XML: Recibe bytes UTF-8 normalizados
  - ✅ CSV: Recibe string UTF-8 normalizado
  - ✅ TXT: Recibe string UTF-8 normalizado
  - ✅ Excel: Recibe bytes (binario preservado)
  - ✅ PDF: Recibe bytes (binario preservado)

- [x] **XML/CSV/XLS/TXT/PDF pasan por normalizers determinísticos**
  - ✅ XML: UTF-8, BOM eliminado, estructura preservada
  - ✅ CSV: UTF-8, delimitador detectado, newlines normalizados (CRLF→LF)
  - ✅ Excel: Binario preservado, encoding de metadatos normalizado
  - ✅ TXT: UTF-8, LF, trimming, whitespace normalizado
  - ✅ PDF: Binario preservado (parser maneja extracción)

- [x] **Sin `FutureWarning` por `if elem:`**
  - ✅ Todos los `if elem:` reemplazados por `if elem is not None:`
  - ✅ Verificado en `xml_parser/parser.py`

- [x] **Endpoint universal entrega DTO/errores 409/422/415/400 correctos**
  - ✅ 409: Duplicado (idempotencia)
  - ✅ 422: Validación fallida
  - ✅ 415: Tipo no soportado
  - ✅ 400: Error de parsing/normalización

- [x] **Workspace (modal Importar) invoca `/api/v1/core/documentos/upload/?preview=true` sin `?async=true`**
  - ✅ Verificado en `facturas.ui.js`: usa `preview=true`
  - ✅ No hay referencias a `async=true`
  - ✅ Maneja feedback con mensajes canónicos

---

## 📊 METADATOS DE NORMALIZACIÓN

La función `normalize_content()` retorna metadatos de limpieza:

```python
{
    "media_type": "xml|csv|excel|txt|pdf",
    "normalized": bytes|str|DataFrame,
    "meta": {
        "encoding": "utf-8",
        "bom_stripped": true|false,
        "newline": "LF"|"CRLF->LF"|"CR->LF"|None,
        "decimal": ".",
        "detected_delimiter": ","|";"|"\\t"|None,
        "cleanups": ["bom_removed", "encoding_normalized", "newline_normalized", ...]
    }
}
```

---

## 🔄 FLUJO ACTUALIZADO

```
1. Upload archivo → ingest_service.ingest_document()
2. ⚠️ SIEMPRE: normalize_content() → detecta tipo + normaliza
3. Router recibe contenido NORMALIZADO + media_type
4. Parser consume contenido NORMALIZADO
5. Validación → DTO
6. Retorna DTO (sin persistir)
```

**NO hay bypass, NO hay excepciones, NO hay raw passthrough.**

---

**Última actualización:** 2026-02-10
