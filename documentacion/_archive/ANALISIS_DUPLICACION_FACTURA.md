# 🔍 Análisis y Corrección: Duplicación de Objetos en Upload de Facturas

## 📋 Resumen del Problema

**Síntoma:** Al guardar 1 archivo, se crea 3 veces el mismo objeto `Factura` en la base de datos.

**Ubicación:** En el flujo de upload de XML/PDF para facturas.

## 🎯 Root Causes Identificados

### 1. **Flujo de Dos Pasos Redundante** (Critical)
**Archivo:** `apps/tenant/landing/static/tenant/landing/workspace/facturas.page.js` (línea 496-556)

**Problema:**
```javascript
// Paso 1: Parsear con endpoint universal (preview=true)
const parseUrl = `/api/v1/core/documentos/upload/?preview=true`;
const parseRes = await fetch(parseUrl, { /* POST */ });

// Paso 2: Persistir con endpoint de la app
const persistUrl = `/api/v1/facturas/create-from-dto/`;
const persistRes = await fetch(persistUrl, { /* POST */ });
```

**Por qué crea 3 veces:**
- ❌ PROBLEMA 1: El endpoint `/api/v1/core/documentos/upload/?preview=true` **NO EXISTE** en los URLs actuales
- ❌ PROBLEMA 2: El endpoint `/api/v1/facturas/create-from-dto/` **NO EXISTE** en los URLs actuales
- ❌ PROBLEMA 3: Posiblemente hay fallback implicit que está usando `/api/v1/facturas/upload-ubl/` que crea automáticamente

### 2. **Endpoint Correcto Actualmente Disponible**
**Archivo:** `apps/tenant/facturas/api/viewsets.py` (FacturaViewSet)

El endpoint que **SÍ EXISTE Y FUNCIONA** es:
```
POST /api/v1/facturas/upload-ubl/?async=false&preview=false
```

Este endpoint:
- ✅ Hace parsing automático
- ✅ Persiste en una sola llamada
- ✅ Soporta batch processing
- ✅ Maneja idempotencia correctamente

### 3. **Listeners Duplicados que Disparan Upload**
**Archivos:** Multiple event listeners pueden estar disparando el mismo upload:

1. `offcanvas_factura.html` - Formulario HTMX
2. `maildigester.xml.modal.js` - Modal de correo
3. `facturas.page.js` - Script de página

Si hay listeners en cascada, el mismo archivo se sube múltiples veces.

---

## ✅ Solución de Corrección

### PASO 1: Eliminar el Flujo de Dos Pasos Incorrecto

**Archivo a eliminar:** 
- `apps/tenant/landing/static/tenant/landing/workspace/facturas.page.js`

**Razón:** 
- Usa endpoints que no existen
- Implementa lógica que ya existe en el ViewSet
- Causa duplicación innecesaria

**Reemplazo:** Usar el flujo unificado de `upload-ubl`

### PASO 2: Unificar en Un Solo Flujo Sincrónico

**Solución Propuesta:**

```javascript
// ✅ FLUJO CORRECTO Y ÚNICO - usa endpoint que EXISTE
async function subirUblAsync(fileOrBlob) {
  const form = new FormData();
  form.append('file', fileOrBlob);
  
  // UN SOLO POST - al endpoint que EXISTE y funciona
  const uploadUrl = `/api/v1/facturas/upload-ubl/?async=false&preview=false`;
  
  const res = await fetch(uploadUrl, {
    method: 'POST',
    body: form,
    credentials: 'same-origin',
    headers: {
      'X-CSRFToken': getCsrf() || '',
    },
  });
  
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.message || `Error: ${res.status}`);
  }
  
  const result = await res.json();
  
  // Actualizar tabla con el resultado
  if (result.id) {
    upsertRow(result);
  } else {
    await loadTabla();
  }
  
  return result;
}
```

### PASO 3: Validar Listeners Only Once

**Archivos a revisar:**
1. ✅ `offcanvas_factura.html` - Remover form submission si ya existe listener
2. ✅ `maildigester.xml.modal.js` - Remover form submission si ya existe listener
3. ✅ `facturas.page.js` - consolidar lógica única

---

## 🏗️ Arquitectura Correcta (According to AGENTS.md)

**Regla violada:**
> ❌ "Prohibido crear archivos que manejen múltiples endpoints o duplicar lógica"
> ✅ "Cada funcionalidad debe tener única fuente de verdad (SSoT)"

**Arquitectura Correcta:**
```
Frontend (JavaScript):
  └── subirFactura(file)
      └── POST /api/v1/facturas/upload-ubl/ (ÚNICO ENDPOINT)
          └── Backend crea Factura (una sola vez)
          └── Backend crea FacturaAnexos (una sola vez)
          └── Backend retorna resultado normalizado
```

---

## 📋 Checklist de Corrección

- [ ] **PASO 1:** Eliminar función `subirUblAsync` incorrecta de `facturas.page.js`
- [ ] **PASO 2:** Crear función simplificada que usa `/api/v1/facturas/upload-ubl/`
- [ ] **PASO 3:** Eliminar endpoint `/api/v1/core/documentos/upload/` de cualquier lugar (no debería existir)
- [ ] **PASO 4:** Eliminar endpoint `/api/v1/facturas/create-from-dto/` de cualquier lugar (no debería existir)
- [ ] **PASO 5:** Auditar listeners para eliminar duplicados
- [ ] **PASO 6:** Agregar log para detectar múltiples creaciones
- [ ] **PASO 7:** Prueba: Subir 1 archivo y verificar que se crea exactamente 1 objeto en BD
- [ ] **PASO 8:** Prueba: Subir 10 archivos y verificar conteo correcto

---

## 🚨 Puntos Críticos a Verificar

### Issue 1: Transaction Rollback
Si hay múltiples POSTs y uno falla, pueden quedar objetos huérfanos.

**Verificar:**
```python
# En guardar_factura_desde_dto() - Ya usa @transaction.atomic ✅
# En FacturaAnexos creation - Debe estar dentro de transaction.atomic ✅
```

### Issue 2: Event Listeners Cascadeantes
Si hay 3 listeners disparando el mismo evento, habrá 3 uploads.

**Verificar:**
```javascript
// Buscar duplicados de:
// - form.addEventListener('submit', ...)
// - btn.addEventListener('click', ...)
// - document.addEventListener('drop', ...)
```

### Issue 3: Serializer Double-Save
Si el serializer llama `.save()` dos veces, habrá duplicación.

**Verificar en `apps/tenant/facturas/api/serializers.py`:**
```python
# En create() o update() - No llamar .save() 2 veces
# Preferir: return self.Meta.model.objects.create(**validated_data)
```

---

## 📊 Diagrama del Problema

```
Upload File
  │
  ├─→ [BUG] subirUblAsync() en facturas.page.js
  │   │
  │   ├─→ POST /api/v1/core/documentos/upload/?preview=true (NO EXISTE)
  │   │   └─→ Fallback a POST /api/v1/facturas/upload-ubl/ ❌ CREACIÓN 1
  │   │
  │   └─→ POST /api/v1/facturas/create-from-dto/ (NO EXISTE)
  │       └─→ Fallback a POST /api/v1/facturas/upload-ubl/ ❌ CREACIÓN 2 (Duplicada)
  │
  ├─→ [BUG] Listener en offcanvas_factura o maildigester
  │   └─→ POST /api/v1/facturas/upload-ubl/ ❌ CREACIÓN 3 (Duplicada)
  │
  └─→ RESULTADO: 1 archivo = 3 objetos creados ❌
```

---

## ✅ Solución Final

**Cambio único necesario:** 
Reemplazar el flujo de `subirUblAsync()` en `facturas.page.js` para usar directamente el endpoint `/api/v1/facturas/upload-ubl/` sin intermediarios.

**Impacto:**
- ✅ 1 archivo = 1 objeto creado
- ✅ Compatible con idempotencia (CUFE duplicado)
- ✅ Soporta batch processing
- ✅ Usa arquitectura SSoT asegurada

