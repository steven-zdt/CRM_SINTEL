# Resumen Auditoría: Facturas-Contabilidad v3.7.1

**Fecha:** 2026-05-13  
**Status:** ✅ **CORREGIDO Y DOCUMENTADO**

---

## 🚨 Violación Encontrada (§18 Bounded Contexts)

```python
# apps/tenant/facturas/api/serializers.py: línea 172-178
def get_cuenta_contable_label(self, obj):
    from apps.tenant.contabilidad.models import CuentaContable  # PROHIBIDO
    cuenta = CuentaContable.objects.filter(uuid=...).first()
    return f"{cuenta.codigo} - {cuenta.nombre}"
```

**Problema:** 
- `facturas` importaba directamente el modelo de `contabilidad`
- Viola §18 (Pull Model: apps fuente NO importan contabilidad)
- Viola §2 (Bounded Contexts: comunicación debe ser HTTP, no imports Python)

---

## ✅ Correcciones Ejecutadas (5 cambios)

### 1️⃣ Serializer — Remover import ilegal

**Archivo:** `apps/tenant/facturas/api/serializers.py`

```python
# ANTES
def get_cuenta_contable_label(self, obj):
    from apps.tenant.contabilidad.models import CuentaContable
    cuenta = CuentaContable.objects.filter(...).first()
    return f"{...}" if cuenta else None

# DESPUÉS
def get_cuenta_contable_label(self, obj):
    """§18: cuenta_contable_uuid se resuelve en frontend via JS."""
    return None  # JS lo pre-carga via HTTP
```

✅ **Estado:** Corregido

---

### 2️⃣ Factura API — Agregar getCuentaByUuid()

**Archivo:** `apps/tenant/facturas/static/js/facturas/facturas.api.js`

```javascript
// NUEVO
getCuentaByUuid: (uuid = '') => {
    const url = `/api/v1/contabilidad/cuentas-contables/?uuid=${encodeURIComponent(uuid)}&app_origen=facturas`;
    return window.http('GET', url);
}
```

✅ **Estado:** Implementado

---

### 3️⃣ Template — Eliminar dependencia de serializer

**Archivo:** `apps/tenant/facturas/templates/tenant/facturas/offcanvas_editar_factura.html`

```html
<!-- ANTES -->
<input type="text" value="{% if factura.cuenta_contable_label %}{{ factura.cuenta_contable_label }}{% endif %}">

<!-- DESPUÉS -->
<input type="text" value="">
{# v3.7: cuenta_contable_uuid se pre-carga en JS via getCuentaByUuid() — §18 HTTP pull #}
```

✅ **Estado:** Corregido

---

### 4️⃣ Editor JS — Agregar pre-carga

**Archivo:** `apps/tenant/facturas/static/js/facturas/features/facturas_editor.js`

```javascript
// NEW: Pre-load logic en initCuentaContableSearch()
const initialUuid = uuidInput.value.trim();
if (initialUuid && !searchInput.value.trim()) {
    w.facturasAPI.getCuentaByUuid(initialUuid).then(response => {
        if (response && response.ok && response.data) {
            const results = Array.isArray(response.data) ? response.data : (response.data.results || []);
            if (results.length > 0) {
                const cuenta = results[0];
                searchInput.value = `${cuenta.codigo} - ${cuenta.nombre}`;
            }
        }
    }).catch(err => {
        console.warn('[facturas.editor:cuenta_search] No se pudo pre-cargar cuenta:', err);
    });
}
```

✅ **Estado:** Implementado

---

### 5️⃣ Contabilidad Endpoint — Verificado (ya existe)

**Endpoint:** `GET /api/v1/contabilidad/cuentas-contables/?uuid={uuid}&app_origen=facturas`

- ✅ Ya soporta `?uuid=` (implementado en auditoría clientes v3.6.1)
- ✅ Filtra por `empresa_id` (DSV aplicado)
- ✅ Retorna `{ codigo, nombre, uuid }`

---

## 📊 Flujo de Integración Correcta

```
EDICIÓN DE FACTURA:
  1. offcanvas abre
  2. JS lee #factura-cuenta_contable_uuid (UUID)
  3. Si UUID existe → facturasAPI.getCuentaByUuid(uuid)
  4. HTTP GET /api/v1/contabilidad/cuentas-contables/?uuid={uuid}
  5. ViewSet retorna { codigo: "130505", nombre: "Clientes", uuid: "..." }
  6. JS pre-llena: "130505 - Clientes"
  
BÚSQUEDA DE CUENTA:
  1. Usuario escribe "130"
  2. JS llama facturasAPI.searchCuentas("130")
  3. HTTP GET /api/v1/contabilidad/cuentas-contables/?search=130
  4. ViewSet retorna array de cuentas
  5. JS renderiza sugerencias
```

---

## 🔍 Verificación de Compliance

| Regla | Status | Detalle |
|-------|--------|---------|
| **§2 Bounded Contexts** | ✅ PASS | Comunicación 100% HTTP, sin imports Python |
| **§18 Pull Model** | ✅ PASS | Contabilidad NO importa facturas; facturas llama endpoints |
| **§13 DSV/IDOR** | ✅ PASS | CuentaContableViewSet filtra por empresa_id |
| **§14 UUID Snapshot** | ✅ PASS | Factura.cuenta_contable_uuid es UUIDField opaco, sin FK |
| **§22 CSS Isolation** | ✅ PASS | Sin `<link>` cross-app en templates |
| **§23 JS Isolation** | ✅ PASS | `facturasAPI.*` es HTTP, no namespace calls |
| **§4 Zero Waste** | ✅ PASS | Queries usan `.only()`, no bare `.all()` |

---

## 📚 Documentación Generada

**Auditoría Completa:**
`apps/tenant/facturas/.agent/AUDITORIA_INTEGRACION_FACTURAS_CONTABILIDAD.md`

Incluye:
- Análisis detallado de la violación
- Descripción de cada corrección
- Diagramas de flujo
- Comparación con patrón coherente (clientes v3.6.1)

---

## 🔗 Referencias

**Arquitectura base:**
- `AGENTS.md` § 2, 4, 13, 14, 18, 22, 23
- `apps/tenant/clientes/.agent/AUDITORIA_INTEGRACION_CLIENTES_CONTABILIDAD.md` (patrón referencia)

**Cambios relacionados:**
- `apps/tenant/contabilidad/api/viewsets.py` — CuentaContableViewSet.get_queryset() ya soporta `?uuid=`

---

**✅ INTEGRACIÓN CORRECTA — AUDITORÍA COMPLETADA**
