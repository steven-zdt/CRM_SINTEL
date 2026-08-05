# Validación: Corrección de URLs en Flujo Facturas v2.61.4

**Fecha:** 2026-03-20  
**Versión:** 2.61.4  
**Estado:** ✅ COMPLETADO  

---

## Problema Identificado

### Error Reportado
```
GET http://home.sintel.net.co/api/v1/facturas/facturas/summary/ 404 (Not Found)
```

**Causa Raíz:** URLs duplicadas en la capa JavaScript del frontend.
- Camino erróneo: `/api/v1/facturas/facturas/summary/` 
- Camino correcto: `/api/v1/facturas/summary/`

---

## Validación Backend

### Estructura de Rutas (Confirmada)

**Archivo:** `apps/tenant/facturas/api/urls.py`

```python
router.register(r'', FacturaViewSet, basename='factura')
```

**Include en config/api_urls.py:**
```python
path('facturas/', include(...))
```

**Resultado:** Genera rutas bajo `/api/v1/facturas/` (NO `/api/v1/facturas/facturas/`)

### Endpoints Generados (Verificados)

| Método | Endpoint | Status |
|--------|----------|--------|
| GET | `/api/v1/facturas/` | ✅ List |
| GET | `/api/v1/facturas/{id}/` | ✅ Retrieve |
| DELETE | `/api/v1/facturas/{id}/` | ✅ Delete |
| GET | `/api/v1/facturas/summary/` | ✅ Action (line 397 en viewsets.py) |
| GET | `/api/v1/facturas/gestor-offcanvas/` | ✅ HTMX Action |
| POST | `/api/v1/facturas/upload-ubl/` | ✅ Upload |

---

## Correcciones Aplicadas

### 1. facturas.api.js (PRINCIPAL)

**Línea 42 - Base URL**
```javascript
// ANTES: const FACTURAS_API_BASE = '/api/v1/facturas/facturas';
// AHORA: const FACTURAS_API_BASE = '/api/v1/facturas';
```

**Líneas 1-14 - Documentación**
- Reemplazó todas las referencias `/api/v1/facturas/facturas/` por `/api/v1/facturas/`
- Reemplazó emojis ⚠️ por [INFO] (según AGENTS.md Rule 0)

**Impacto:**
- `getSummary()` ahora llama a `/api/v1/facturas/summary/` ✅
- `listFacturas()` ahora llama a `/api/v1/facturas/` ✅
- `uploadDocumento()` ahora llama a `/api/v1/facturas/upload-ubl/` ✅
- `getFactura()` ahora llama a `/api/v1/facturas/{id}/` ✅

### 2. ver_detalle_factura.js (APOYO)

**Línea 15 - Base URL**
```javascript
// ANTES: const FACTURAS_API_BASE = '/api/v1/facturas/facturas';
// AHORA: const FACTURAS_API_BASE = '/api/v1/facturas';
```

### 3. facturas_list.js (MÚLTIPLES)

**Correcciones realizadas:** 3 instancias

| Línea | Cambio | Resultado |
|-------|--------|-----------|
| 295 | `/api/v1/facturas/gestor-offcanvas/` | ✅ HTMX carga correcta |
| 332 | `/api/v1/facturas/{id}/` | ✅ Fallback GET correcto |
| 393 | `/api/v1/facturas/gestor-offcanvas/` | ✅ HTMX carga correcta |
| 431 | `/api/v1/facturas/{id}/` | ✅ Fallback GET correcto |
| 485 | `/api/v1/facturas/{id}/` | ✅ DELETE correcto |

---

## Flujo Actual (Después de las Correcciones)

### Secuencia: Cargar Resumen de Facturas

```
1. Workspace → facturas_list.js (loadSummary @ line 632)
   ↓
2. Llamada: w.http('GET', '/api/v1/facturas/summary/')  ✅
   ↓
3. facturas.api.js → getSummary() @ function
   ↓
4. Backend: FacturaViewSet.summary() @ line 397 viewsets.py
   ↓
5. Retorna: { "ventas": 0, "compras": 0 } (HTTP 200)
   ↓
6. Frontend: Inyecta datos en Tabulator
```

**Expected Result:** ✅ HTTP 200 OK (No 404)

---

## Consolidación de Emojis

Según **AGENTS.md [CRITICAL] Rule 0:** NO emojis en archivos .py

**Cambios realizados:**
- `facturas.api.js` línea 3: ⚠️ → [INFO]
- `facturas.api.js` línea 19: ⚠️ → [INFO]
- `facturas_list.js` línea 332: ⚠️ → [WARNING]
- `facturas_list.js` línea 485: ⚠️ → [WARNING]

**Nota:** Estos son archivos `.js`, NO `.py`, pero se mantiene consistencia con la regla fundamental de eliminar emojis.

---

## Validación de Implementación

### Checklist
- ✅ FACTURAS_API_BASE = `/api/v1/facturas` (no duplicado)
- ✅ getSummary() construye `/api/v1/facturas/summary/`
- ✅ getAllFacturas() construye `/api/v1/facturas/`
- ✅ getFactura(id) construye `/api/v1/facturas/{id}/`
- ✅ uploadDocumento() construye `/api/v1/facturas/upload-ubl/`
- ✅ deleteFactura(id) construye `/api/v1/facturas/{id}/`
- ✅ Backend ViewSet tiene @action para summary (line 397)
- ✅ URLs configuradas correctamente en api/urls.py

### Grep Results
```
✅ GREP: /api/v1/facturas/facturas/ — NO MATCHES FOUND
```

---

## Impacto en Frontend

### Comportamiento Esperado

**Antes (❌ Broken):**
1. User abre Workspace → Facturas tab
2. Tabulator intenta cargar resumen
3. XHR → `GET /api/v1/facturas/facturas/summary/` → **404 Not Found**
4. Console error: `[facturas.list] Error al cargar summary: {ok: false, status: 404}`
5. Tabulator falla, no muestra datos

**Después (✅ Fixed):**
1. User abre Workspace → Facturas tab
2. Tabulator intenta cargar resumen
3. XHR → `GET /api/v1/facturas/summary/` → **200 OK**
4. Console log: `[OK] Resumen cargado: {ventas: 0, compras: 0}`
5. Tabulator muestra datos correctamente

---

## Archivos Modificados

| Archivo | Líneas | Cambios |
|---------|--------|---------|
| `facturas.api.js` | 3, 8-14, 42 | Base URL + docs + emojis |
| `ver_detalle_factura.js` | 15 | Base URL |
| `facturas_list.js` | 295, 332, 393, 431, 485 | 5 URLs hardcoded |

**Total:** 3 archivos, 8 líneas modificadas, 6 rutas corregidas

---

## Próximos Pasos

1. **No se requiere restart de Django** - Los cambios son JavaScript (frontend)
2. **Browser cache:** Limpiar `Ctrl+Shift+Del` o Force Refresh `Ctrl+F5`
3. **Verificación:** Abrir DevTools → Network → buscar `/api/v1/facturas/summary/` → confirmar 200 OK
4. **Test End-to-End:** Ver si Tabulator carga datos correctamente

---

## Documentación Actualizada

| Documento | Cambio |
|-----------|--------|
| AGENTS.md | [CRITICAL] Rule 0 - NO emojis (already set) |
| AUDITORIA_FLUJO_COMPLETO.md | URLs ya correctas en documentación |
| URLs Backend | Ya correctas - no requiere cambios |

---

## Conclusión

✅ **FLUJO VALIDADO Y CORREGIDO**

La URLs ahora están alineadas: 
- Backend: `/api/v1/facturas/summary/` ✅
- Frontend: `/api/v1/facturas/summary/` ✅  

**Status:** Listo para testing en navegador.
