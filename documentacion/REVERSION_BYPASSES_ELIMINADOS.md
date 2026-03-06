# 🗑️ BYPASSES Y FLAGS ELIMINADOS — Normalización Completa

**Fecha:** 2026-02-10  
**Objetivo:** Listar todos los bypasses, flags y rutas alternativas que fueron eliminados para forzar normalización SIEMPRE.

---

## 📋 BYPASSES ELIMINADOS

### 1. Condicional `should_normalize` en `ingest_service.py`

**Antes:**
```python
should_normalize = detected_media_type in ("pdf", "excel")
if should_normalize:
    normalized_content = normalize_encoding(content)
else:
    normalized_content = content  # ⚠️ BYPASS
```

**Después:**
```python
# ⚠️ REVERSIÓN: Normalización SIEMPRE aplicada
normalization_result = normalize_content(...)
normalized_content = normalization_result.get("normalized")
```

**Estado:** ✅ **ELIMINADO**

---

### 2. Log `document_ingest_skip_normalization`

**Antes:**
```python
logger.info("document_ingest_skip_normalization", ...)
```

**Después:**
```python
# Ya no existe este log
logger.info("document_ingest_normalization_ok", ...)  # Siempre se registra
```

**Estado:** ✅ **ELIMINADO**

---

### 3. Fallback a contenido original en detección fallida

**Antes:**
```python
except Exception as e:
    # Si falla la detección, usar contenido original (fallback seguro)
    normalized_content = content  # ⚠️ BYPASS
```

**Después:**
```python
except ValueError as e:
    # Tipo no reconocido o contenido insalvable
    return {...}, 415  # ⚠️ NO hay bypass, se retorna error
```

**Estado:** ✅ **ELIMINADO**

---

### 4. Detección duplicada en router

**Antes:**
```python
# Router siempre detectaba tipo de nuevo
detection_result = detect_document_type(file_bytes, filename, mime_type)
```

**Después:**
```python
# Router usa media_type del normalizer si está disponible
if not media_type:
    detection_result = detect_document_type(...)  # Solo si no viene del normalizer
else:
    confidence = 1.0  # Ya viene del normalizer
```

**Estado:** ✅ **OPTIMIZADO** (evita detección duplicada)

---

## 🚫 FLAGS NO ENCONTRADOS (Verificación)

### Flags que NO existen en el repo:

- ✅ `skip_normalization`: No encontrado
- ✅ `bypass_normalization`: No encontrado
- ✅ `raw_passthrough`: No encontrado
- ✅ `fast_path`: No encontrado
- ✅ `ALLOW_RAW_UPLOAD`: No encontrado
- ✅ `FEATURE_*_NORMAL`: No encontrado

**Estado:** ✅ **No hay flags de bypass en el código**

---

## ✅ RUTAS ALTERNATIVAS ELIMINADAS

### 1. Ruta "raw passthrough" para XML/CSV/TXT

**Antes:**
```python
# Para XML/CSV/TXT, usar contenido original sin normalizar
normalized_content = content
```

**Después:**
```python
# ⚠️ REVERSIÓN: TODOS los tipos pasan por normalización
normalization_result = normalize_content(...)
```

**Estado:** ✅ **ELIMINADO**

---

### 2. Short-circuit en detección fallida

**Antes:**
```python
except Exception as e:
    normalized_content = content  # Short-circuit
```

**Después:**
```python
except ValueError as e:
    return {...}, 415  # Error determinístico
```

**Estado:** ✅ **ELIMINADO**

---

## 📊 RESUMEN DE ELIMINACIONES

| Bypass/Flag | Ubicación | Estado |
|-------------|-----------|--------|
| `should_normalize` condicional | `ingest_service.py` | ✅ ELIMINADO |
| `skip_normalization` log | `ingest_service.py` | ✅ ELIMINADO |
| Fallback a `content` original | `ingest_service.py` | ✅ ELIMINADO |
| Detección duplicada | `router.py` | ✅ OPTIMIZADO |
| Ruta "raw passthrough" | `ingest_service.py` | ✅ ELIMINADO |
| Short-circuit en excepciones | `ingest_service.py` | ✅ ELIMINADO |

---

## ✅ GARANTÍAS ACTUALES

1. **Normalización SIEMPRE aplicada:**
   - ✅ XML: UTF-8, BOM eliminado
   - ✅ CSV: UTF-8, delimitador detectado, newlines normalizados
   - ✅ Excel: Binario preservado, encoding normalizado
   - ✅ TXT: UTF-8, LF, trimming, whitespace
   - ✅ PDF: Binario preservado

2. **NO hay bypass:**
   - ✅ No hay condiciones que salten normalización
   - ✅ No hay fallbacks a contenido original
   - ✅ No hay rutas alternativas

3. **Errores determinísticos:**
   - ✅ 415: Tipo no reconocido
   - ✅ 400: Error de normalización
   - ✅ 422: Error de validación

---

**Última actualización:** 2026-02-10
