# 🔍 DIAGNÓSTICO — Error 422 en Validación de Documentos

**Fecha:** 2026-02-10  
**Problema:** El endpoint `/api/v1/core/documentos/upload/` retorna 422 (Unprocessable Entity) con `document_ingest_validation_failed`

---

## 📋 ANÁLISIS DEL PROBLEMA

### Logs Observados:
```
[WARNING] apps.services.document_ingest: document_ingest_validation_failed
[WARNING] django.request: Unprocessable Entity: /api/v1/core/documentos/upload/
[WARNING] django.server: "POST /api/v1/core/documentos/upload/?async=true HTTP/1.1" 422
```

### Posibles Causas:

1. **CUFE/UUID faltante o vacío**
   - El validador `FacturaValidator` requiere `identificadores.cufe` o `identificadores.uuid`
   - Si el XML no tiene UUID, la validación falla

2. **Fecha de emisión inválida**
   - El validador verifica que `fecha_emision` esté en formato válido
   - Si el formato no coincide con los formatos esperados, falla

3. **Totales incoherentes**
   - El validador verifica que `subtotal + impuestos ≈ total` (tolerancia 0.01)
   - Si no coincide, falla

4. **Campos comunes faltantes**
   - `validate_common_fields()` verifica: `numero`, `identificadores`, `fecha_emision`, `emisor`, `receptor`, `totales`
   - Si alguno falta o está vacío, falla

5. **Tipo de documento no encontrado**
   - Si el DTO no tiene `type` o `document_type`, `run_validations()` retorna `validator_not_found`
   - Esto debería activar el fallback a validación genérica

---

## 🔧 MEJORAS APLICADAS

### 1. Logging Mejorado en `ingest_service.py`

Se agregó logging detallado para identificar exactamente qué está fallando:

```python
logger.warning(
    "document_ingest_validation_failed",
    extra={
        "request_id": request_id,
        "schema_name": schema,
        "document_type": document_type,
        "dto_type": dto_dict.get("type"),
        "dto_document_type": dto_dict.get("document_type"),
        "error_code": error_code,
        "missing_fields": missing_fields[:10],
        "dto_keys": list(dto_dict.keys())[:20],
        "has_numero": bool(dto_dict.get("numero")),
        "has_identificadores": bool(dto_dict.get("identificadores")),
        "has_fecha_emision": bool(dto_dict.get("fecha_emision")),
        "has_totales": bool(dto_dict.get("totales")),
    }
)
```

---

## 📊 PRÓXIMOS PASOS PARA DIAGNÓSTICO

### 1. Revisar Logs Detallados

Después de aplicar el cambio, los logs mostrarán:
- Qué campos están faltando exactamente
- Si el DTO tiene los campos básicos (`has_numero`, `has_identificadores`, etc.)
- Qué tipo de documento se detectó
- Qué error_code específico se generó

### 2. Verificar XML de Entrada

Si el XML no tiene UUID/CUFE, el parser debería:
- Extraer el UUID del XML si existe
- Si no existe, el validador debería ser más flexible (o el XML es inválido)

### 3. Verificar Formato de Fecha

El parser XML genera fechas en formato ISO 8601. Si el XML tiene un formato diferente, puede fallar.

### 4. Verificar Totales

Si los totales no son coherentes, puede ser:
- Error en el XML original
- Error en el cálculo del parser
- Redondeo de decimales

---

## ✅ SOLUCIÓN TEMPORAL

Si el problema es que el XML no tiene UUID/CUFE (documentos de prueba), se puede:

1. **Hacer el CUFE opcional en validación** (solo para desarrollo)
2. **Usar el número de documento como identificador alternativo**
3. **Permitir documentos sin CUFE en modo preview**

---

**Última actualización:** 2026-02-10
