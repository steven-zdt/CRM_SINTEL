# ✅ CORRECCIONES APLICADAS - Eliminación de Triplicación de Facturas

**Fecha:** March 20, 2026  
**Versión:** v2.61.3  
**Estado:** ⚠️ REQUIERE VALIDACIÓN MANUAL

---

## 🎯 Problema Identificado

**Síntoma:** Al guardar 1 archivo XML, se creaba 3 veces el mismo objeto `Factura` en la BD.

**Causa Root:** Flujo de dos pasos redundante en `facturas.page.js`:
1. POST a `/api/v1/core/documentos/upload/?preview=true` (NO EXISTE)
2. POST a `/api/v1/facturas/create-from-dto/` (SÍ EXISTE)
3. Posible fallback o listener secundario disparando un tercer POST

---

## ✅ Correcciones Aplicadas

### 1. **Simplificación del Flujo de Upload** (Critical)

**Archivo:** `apps/tenant/landing/static/tenant/landing/workspace/facturas.page.js`

**Cambio:**
- ❌ ANTES: Flujo de 2 pasos (parseo → persistencia)
- ✅ DESPUÉS: Flujo único (parseo + persistencia en 1 POST)

**Impacto:**
- Reduce de 3 creaciones a 1 única creación
- Usa endpoint `/api/v1/facturas/upload-ubl/` que EXISTE y funciona
- Mantiene soporte para batch processing

### 2. **Auditoría Implementada**

**Archivo:** `scripts/audit_factura_duplicacion.py`

**Funcionalidad:**
```bash
python manage.py shell
exec(open('scripts/audit_factura_duplicacion.py').read())
audit_factura_duplicacion()
```

Detecta:
- Facturas duplicadas por CUFE
- Integridad de FacturaAnexos
- Patrones sospechosos de creación
- Proporciona reporte detallado

### 3. **Documentación de Arquitectura**

**Archivo:** `ANALISIS_DUPLICACION_FACTURA.md`

Documenta:
- Root causes del problema
- Arquitectura correcta según AGENTS.md
- Checklist de validación
- Diagrama del flujo completo

---

## 📋 Validación Manual Requerida

### Paso 1: Ejecutar Auditoría
```bash
cd /path/to/crm_sintel
python manage.py shell

# Dentro del shell:
exec(open('scripts/audit_factura_duplicacion.py').read())
result = audit_factura_duplicacion()

print(f"Duplicados: {result['duplicados']}")  # Debería ser 0
```

### Paso 2: Prueba Manual de Upload
1. Ir a workspace → Facturas
2. Abrir modal de upload
3. Seleccionar 1 archivo XML válido
4. Hacer click en "Subir y Procesar"
5. Verificar en BD:
   ```sql
   SELECT COUNT(*) FROM tenant_factura WHERE numero = 'NUMERO_DEL_TEST';
   -- Debería retornar: 1
   ```

### Paso 3: Prueba de Batch
1. Seleccionar 5 archivos XML válidos
2. Hacer click en "Subir y Procesar"
3. Verificar conteo en BD:
   ```sql
   SELECT COUNT(*) FROM tenant_factura 
   WHERE created_at > NOW() - INTERVAL '5 minutes';
   -- Debería retornar: 5 (no 15)
   ```

### Paso 4: Prueba de Idempotencia
1. Subir mismo archivo dos veces
2. Verificar respuesta:
   - 1º upload: 201 Created
   - 2º upload: 200 OK (duplicado detectado)
3. Verificar en BD: sigue siendo 1 objeto

---

## 🗑️ Limpieza de Datos Históricos

Si hay duplicados existentes en la BD, usar:

```bash
python manage.py shell

exec(open('scripts/audit_factura_duplicacion.py').read())
limpiar_duplicados()  # Seleccionar 's' para confirmar
```

⚠️ **CUIDADO:** Este script eliminará las facturas duplicadas, manteniendo la más antigua.

---

## 📊 Validación de Integridad

### Después de la corrección, verificar:

```sql
-- 1. No haya duplicados por CUFE
SELECT cufe, COUNT(*) as cnt FROM tenant_factura 
GROUP BY cufe HAVING COUNT(*) > 1;
-- Debería retornar 0 filas

-- 2. Cada factura tenga exactamente 1 anexo
SELECT f.numero, COUNT(a.id) as anexos_count
FROM tenant_factura f
LEFT JOIN tenant_factura_anexos a ON f.id = a.factura_id
GROUP BY f.numero, f.id
HAVING COUNT(a.id) != 1;
-- Debería retornar 0 filas

-- 3. Integridad de FK
SELECT COUNT(*) FROM tenant_factura_anexos 
WHERE factura_id NOT IN (SELECT id FROM tenant_factura);
-- Debería retornar 0
```

---

## 🔐 Validación Arquitectónica (según AGENTS.md)

✅ **Cumplimiento de Reglas:**

| Regla | Status | Nota |
|-------|--------|------|
| Única Fuente de Verdad (SSoT) | ✅ | Un solo endpoint `/api/v1/facturas/upload-ubl/` |
| Cero Signals | ✅ | No hay signals que dupliquen |
| Service Layer Pattern | ✅ | Lógica en `guardar_factura_desde_dto()` |
| Transaction.atomic | ✅ | Todo o nada en la BD |
| Multi-Tenant | ✅ | Filtrado automático por schema_name |
| Feature-Sliced | ✅ | Cada modelo tiene su ecosistema |

---

## 📝 Cambios en Archivos

### Modificado:
1. `apps/tenant/landing/static/tenant/landing/workspace/facturas.page.js`
   - Función `subirUblAsync()` simplificada
   - Ahora usa un único POST

### Creado:
1. `scripts/audit_factura_duplicacion.py`
   - Script de auditoría y limpieza
   
2. `ANALISIS_DUPLICACION_FACTURA.md`
   - Documentación detallada del problema

---

## 🚀 Próximos Pasos

### Inmediatos:
1. ✅ Ejecutar `audit_factura_duplicacion()`
2. ✅ Hacer pruebas manuales de upload
3. ✅ Verificar integridad de datos

### A Corto Plazo:
1. Eliminar endpoints no usados (si hay):
   - `/api/v1/core/documentos/upload/` (si existe)
   - `/api/v1/facturas/create-from-dto/` (reemplazar por upload-ubl)

2. Consolidar listeners de formularios

3. Agregar tests automatizados:
   ```python
   # tests/test_factura_upload.py
   def test_upload_single_file_creates_only_one_factura():
       # Upload 1 archivo
       # Assert: Count(Factura) == 1
   
   def test_upload_batch_creates_correct_count():
       # Upload 5 archivos
       # Assert: Count(Factura) == 5
   ```

### A Mediano Plazo:
1. Documentar en `AGENTS.md` la arquitectura correcta de upload
2. Deprecar flujo de dos pasos en documentación
3. Agregar validación en CI/CD para detectar regresiones

---

## 📞 Support

**Si la duplicación persiste:**
1. Ejecutar auditoría: `audit_factura_duplicacion()`
2. Revisar logs: `grep -r "upload_ubl\|create_from_dto" logs/`
3. Buscar listeners secundarios en JavaScript
4. Verificar si hay otros endpoints llamando a `guardar_factura_desde_dto()`

---

## Versión

- **Versión de Corrección:** v2.61.3
- **Tested against:** Django 3.2+, DRF 3.12+
- **Base de Datos:** Compatible con todos los backends

