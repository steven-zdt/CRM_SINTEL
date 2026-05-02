# Fix Eliminación Cuentas Contables - v2.61

**Fecha:** 2024-12-19  
**Estado:** ✅ Implementado  
**Versión:** 2.61

---

## 📋 Resumen

Corrección del problema de eliminación de cuentas contables que causaba errores 404 y 422, y mejoras en el manejo de errores del frontend para mostrar mensajes de validación correctamente.

---

## 🐛 Problemas Identificados

### 1. Error 404 - ID None
**Síntoma:** `DELETE /api/v1/contabilidad/cuentas-contables/2/` retornaba 404  
**Causa:** `BaseTenantViewSet` usa `lookup_field="uuid"`, pero el frontend envía IDs numéricos. El router de DRF ponía el valor numérico en `kwargs['uuid']` en lugar de `kwargs['pk']`, causando que `get_object()` fallara al buscar un UUID inválido.

**Logs:**
```
[INFO] CuentaContableViewSet.destroy llamado con kwargs: {'uuid': '2'}, uuid: 2, pk: None
[WARNING] Not Found: /api/v1/contabilidad/cuentas-contables/2/
```

### 2. Error 422 - Mensaje no visible
**Síntoma:** Error 422 retornado pero mensaje no se mostraba en el frontend  
**Causa:** `UIManager.handleError` no manejaba correctamente el formato de respuesta de `http.js` y no extraía correctamente el mensaje de `response.data.detail` cuando era un array.

**Logs:**
```
[UIManager][cuentas] DEBUG - responseData extraído: {detail: Array(1)}
[UIManager][cuentas] DEBUG - Mensaje de array detail: Cuenta contable con ID None no encontrada.
```

---

## ✅ Soluciones Implementadas

### 1. ViewSet - Detección Inteligente de ID/UUID

**Archivo:** `apps/tenant/contabilidad/api/viewsets.py`

**Cambios:**
- Detección automática si el identificador es numérico (pk) o UUID
- Si es numérico → busca por `pk` directamente
- Si es UUID → usa `get_object()` con `lookup_field="uuid"`
- Validación y logging completo para diagnóstico

**Código:**
```python
def destroy(self, request, *args, **kwargs):
    # Obtener identificador (puede venir como 'uuid' o 'pk' en kwargs)
    cuenta_identifier = kwargs.get('uuid') or kwargs.get('pk')
    
    # Detectar si es numérico (pk) o UUID
    try:
        # Intentar convertir a entero (es un ID numérico)
        cuenta_id = int(cuenta_identifier)
        cuenta = CuentaContable.objects.get(id=cuenta_id)
    except (ValueError, TypeError):
        # No es numérico, intentar como UUID
        cuenta = self.get_object()  # Usa lookup_field="uuid"
        cuenta_id = cuenta.id
    
    delete_cuenta(cuenta_id)
    return Response(status=status.HTTP_204_NO_CONTENT)
```

**Beneficios:**
- ✅ Compatible con frontend que envía IDs numéricos
- ✅ Compatible con API que usa UUIDs
- ✅ Detección automática sin cambios en el frontend

---

### 2. UIManager - Soporte para Formato HTTP.js

**Archivo:** `apps/tenant/core/static/core/js/lib/ui-manager.js`

**Cambios:**
- Soporte para formato de `http.js`: `{ ok: boolean, status: number, data: object }`
- Extracción correcta de mensajes de `response.data.detail` cuando es array
- Manejo de contenedores de página (no solo modales)
- Logs de depuración para diagnóstico

**Código:**
```javascript
handleError: function (htmxDetailOrResponse, moduleName, options = {}) {
    let responseData = {};
    
    // Soporte para dos formatos:
    // 1. HTMX format: { xhr: XMLHttpRequest }
    // 2. HTTP.js format: { ok: boolean, status: number, data: object }
    if (htmxDetailOrResponse && htmxDetailOrResponse.xhr) {
        // Formato HTMX
        responseData = JSON.parse(htmxDetailOrResponse.xhr.responseText);
    } else if (htmxDetailOrResponse && typeof htmxDetailOrResponse === 'object' && 'status' in htmxDetailOrResponse) {
        // Formato HTTP.js
        responseData = htmxDetailOrResponse.data || {};
    }
    
    // Manejar detail como string, array u objeto
    if (responseData.detail) {
        if (Array.isArray(responseData.detail)) {
            detailMessage = responseData.detail.join(', ');
        } else if (typeof responseData.detail === 'string') {
            detailMessage = responseData.detail;
        }
        // ... renderizar en contenedor
    }
}
```

**Beneficios:**
- ✅ Muestra mensajes de error del backend correctamente
- ✅ Soporta arrays de mensajes de validación
- ✅ Funciona con contenedores de página y modales

---

### 3. Frontend - Validación y Normalización de IDs

**Archivo:** `apps/tenant/core/static/core/js/contabilidad/cuentas.page.js`

**Cambios:**
- Validación del ID en el formatter de Tabulator
- Normalización del ID extraído del botón
- Validación del ID antes de construir URL
- Logs de depuración para rastrear el flujo

**Código:**
```javascript
// En formatter de columna Acciones
formatter: function(cell) {
    let cuentaId = rowData.id;
    // Validar y normalizar ID
    if (!cuentaId || cuentaId === null || cuentaId === undefined) {
        return '-';
    }
    cuentaId = String(cuentaId).trim();
    // ... renderizar botones con data-id="${cuentaId}"
}

// En handleEliminarCuenta
async function handleEliminarCuenta(id) {
    // Normalizar ID
    const normalizedId = String(id).trim();
    if (!normalizedId || normalizedId === 'undefined' || normalizedId === 'null') {
        return;
    }
    // Construir URL y hacer DELETE
}
```

**Beneficios:**
- ✅ IDs siempre válidos y normalizados
- ✅ Prevención de errores por IDs inválidos
- ✅ Logs para diagnóstico

---

## 📊 Flujo Completo

### Eliminación Exitosa
1. Usuario hace click en botón "Eliminar"
2. Frontend extrae ID del botón (`data-id`)
3. Frontend construye URL: `/api/v1/contabilidad/cuentas-contables/{id}/`
4. Frontend envía `DELETE` request
5. Backend detecta que ID es numérico
6. Backend busca cuenta por `pk`
7. Backend valida reglas de negocio (cuentas hijas, movimientos)
8. Backend elimina cuenta
9. Frontend recarga tabla
10. Frontend muestra mensaje de éxito

### Eliminación Rechazada (Validación)
1. Usuario hace click en botón "Eliminar"
2. Frontend extrae ID y envía `DELETE`
3. Backend detecta ID numérico y busca cuenta
4. Backend valida reglas de negocio
5. Backend retorna 422 con `{"detail": ["mensaje de validación"]}`
6. Frontend recibe respuesta 422
7. `UIManager.handleError` extrae mensaje del array `detail`
8. Frontend muestra mensaje en `#error-container-cuentas`
9. Usuario ve mensaje: "No se puede eliminar una cuenta que tiene cuentas hijas asociadas."

---

## 🔍 Validaciones de Negocio

El servicio `delete_cuenta()` valida:

1. **Cuenta existe:** Verifica que la cuenta con el ID proporcionado exista
2. **Sin cuentas hijas:** No se puede eliminar si tiene `cuentas_hijas.exists()`
3. **Sin movimientos:** No se puede eliminar si tiene `MovimientoContable.objects.filter(cuenta=cuenta).exists()`

**Mensajes de error:**
- `"Cuenta contable con ID {id} no encontrada."` (404)
- `"No se puede eliminar una cuenta que tiene cuentas hijas asociadas."` (422)
- `"No se puede eliminar una cuenta que tiene movimientos contables asociados."` (422)

---

## 📝 Archivos Modificados

### Backend
- `apps/tenant/contabilidad/api/viewsets.py`
  - Método `destroy()` actualizado con detección inteligente de ID/UUID
  - Validación y logging mejorados

### Frontend
- `apps/tenant/core/static/core/js/lib/ui-manager.js`
  - Soporte para formato HTTP.js
  - Manejo de arrays en `response.data.detail`
  - Soporte para contenedores de página

- `apps/tenant/core/static/core/js/contabilidad/cuentas.page.js`
  - Validación y normalización de IDs
  - Logs de depuración
  - Manejo de errores mejorado

---

## ✅ Checklist de Validación

- [x] ViewSet detecta IDs numéricos correctamente
- [x] ViewSet busca por `pk` cuando el ID es numérico
- [x] ViewSet busca por `uuid` cuando el identificador es UUID
- [x] UIManager extrae mensajes de arrays correctamente
- [x] UIManager muestra errores en contenedores de página
- [x] Frontend valida IDs antes de enviar requests
- [x] Frontend normaliza IDs correctamente
- [x] Mensajes de error se muestran correctamente
- [x] Logs de depuración funcionan
- [x] Eliminación exitosa funciona
- [x] Eliminación rechazada muestra mensaje correcto

---

## 🎯 Próximos Pasos (Opcional)

1. **Migrar frontend a UUIDs:** Cambiar el frontend para usar UUIDs en lugar de IDs numéricos (alineado con arquitectura)
2. **Tests:** Agregar tests unitarios para `destroy()` con IDs numéricos y UUIDs
3. **Documentación API:** Actualizar documentación para indicar soporte de ambos formatos

---

## 📚 Referencias

- `apps/tenant/contabilidad/api/viewsets.py` - Implementación del ViewSet
- `apps/tenant/contabilidad/services/cuentas_service.py` - Lógica de negocio
- `apps/tenant/core/static/core/js/lib/ui-manager.js` - Manejo de errores
- `apps/tenant/core/static/core/js/contabilidad/cuentas.page.js` - Frontend
- `apps/tenant/api/base.py` - BaseTenantViewSet con lookup_field="uuid"

---

**Última actualización:** 2024-12-19  
**Versión del documento:** 1.0
