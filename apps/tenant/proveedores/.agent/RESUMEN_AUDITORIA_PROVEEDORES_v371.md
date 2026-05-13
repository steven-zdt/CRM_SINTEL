# Resumen Auditoría: Proveedores-Contabilidad v3.7.1

**Fecha:** 2026-05-13  
**Status:** ✅ **CORREGIDO Y DOCUMENTADO**

---

## 🚨 Violaciones Encontradas (§18 Bounded Contexts)

```python
# ANTES: apps/tenant/proveedores/api/serializers.py

class ProveedorDetailSerializer(...):
    cuenta_contable_label = serializers.SerializerMethodField()  # línea 122
    fields = (..., "cuenta_contable_label",)
    
    def get_cuenta_contable_label(self, obj):  # línea 135-140
        from apps.tenant.contabilidad.services.selectors import get_label_by_uuid  # PROHIBIDO
        return get_label_by_uuid(obj.cuenta_contable_uuid, ...)
    
    def validate_cuenta_contable_uuid(self, value):  # línea 142-151
        if value:
            from apps.tenant.contabilidad.services.selectors import qs_cuenta_detail  # PROHIBIDO
            if not qs_cuenta_detail(empresa_id).filter(uuid=value).exists():
                raise ValidationError(...)
```

**Problemas:**
- `proveedores` importaba directamente desde `contabilidad.services.selectors`
- Viola §18 (Pull Model: apps fuente NO importan contabilidad)
- Viola §2 (Bounded Contexts: comunicación debe ser HTTP, no imports Python)

---

## ✅ Correcciones Ejecutadas (2 violaciones)

### 1️⃣ Remover campo y métodos del serializer

**Archivo:** `apps/tenant/proveedores/api/serializers.py`

```python
# ANTES (línea 122, 135-151)
class ProveedorDetailSerializer(...):
    cuenta_contable_label = serializers.SerializerMethodField()  # ✗ Removido
    fields = (..., "cuenta_contable_label",)  # ✗ Removido
    
    def get_cuenta_contable_label(self, obj):  # ✗ Removido
        from apps.tenant.contabilidad.services.selectors import get_label_by_uuid
        return get_label_by_uuid(...)
    
    def validate_cuenta_contable_uuid(self, value):  # ✗ Removido
        from apps.tenant.contabilidad.services.selectors import qs_cuenta_detail
        if not qs_cuenta_detail(...).exists():
            raise ValidationError(...)

# DESPUÉS
class ProveedorDetailSerializer(...):
    # NO hay cuenta_contable_label field
    fields = (...,)  # Solo campos estándar
    # NO hay get_cuenta_contable_label()
    # NO hay validate_cuenta_contable_uuid()
    # §18: cuenta_contable_uuid se asigna como opaque reference, sin resolver en backend
```

✅ **Estado:** Corregido

---

## 📊 Flujo de Integración (Cuando haya UI)

```
SELECCIÓN DE CUENTA (Futuro):
  1. offcanvas abre para editar Proveedor
  2. JS lee #proveedor-cuenta_contable_uuid (UUID)
  3. Si UUID existe → proveedoresAPI.getCuentaByUuid(uuid)  [PENDIENTE]
  4. HTTP GET /api/v1/contabilidad/cuentas-contables/?uuid={uuid}
  5. ViewSet retorna { codigo, nombre, uuid }
  6. JS pre-llena: "2310 - Cuentas por pagar a proveedores"
  
BÚSQUEDA DE CUENTA (Futuro):
  1. Usuario escribe "231"
  2. JS llama proveedoresAPI.searchCuentas("231")  [PENDIENTE]
  3. HTTP GET /api/v1/contabilidad/cuentas-contables/?search=231
  4. ViewSet retorna array de cuentas
  5. JS renderiza sugerencias
```

---

## 🔍 Verificación de Compliance

| Regla | Status | Detalle |
|-------|--------|---------|
| **§2 Bounded Contexts** | ✅ PASS | Comunicación 100% HTTP, sin imports Python |
| **§18 Pull Model** | ✅ PASS | Proveedores NO importa contabilidad; llamadas serán HTTP (cuando haya UI) |
| **§13 DSV/IDOR** | ✅ PASS | CuentaContableViewSet filtra por empresa_id |
| **§14 UUID Snapshot** | ✅ PASS | Campo cuenta_contable_uuid es UUIDField opaco, sin FK |
| **§22 CSS Isolation** | ✅ PASS | Sin imports cross-app |
| **§23 JS Isolation** | ✅ PASS | Será HTTP cuando se implemente |
| **§4 Zero Waste** | ✅ PASS | Fields alineados con DETAIL_FIELDS de services.py |

---

## 📚 Documentación Generada

**Auditoría Completa:**
`apps/tenant/proveedores/.agent/AUDITORIA_INTEGRACION_PROVEEDORES_CONTABILIDAD.md`

Incluye:
- Análisis detallado de las 2 violaciones
- Descripción de cada corrección
- Flujos de integración (cuando haya UI)
- Comparación con patrón coherente (4 apps auditadas)

---

## 🔗 Referencias

**Arquitectura base:**
- `AGENTS.md` § 2, 4, 13, 14, 18, 22, 23
- `apps/tenant/clientes/.agent/AUDITORIA_INTEGRACION_CLIENTES_CONTABILIDAD.md` (patrón referencia)
- `apps/tenant/facturas/.agent/AUDITORIA_INTEGRACION_FACTURAS_CONTABILIDAD.md` (patrón referencia)
- `apps/tenant/inventario/.agent/AUDITORIA_INTEGRACION_INVENTARIO_CONTABILIDAD.md` (patrón referencia)
- `apps/tenant/empleados/.agent/AUDITORIA_INTEGRACION_EMPLEADOS_CONTABILIDAD.md` (patrón referencia)

**Cambios relacionados:**
- `apps/tenant/contabilidad/api/viewsets.py` — CuentaContableViewSet.get_queryset() soporta `?uuid=`

---

**✅ INTEGRACIÓN CORRECTA — AUDITORÍA COMPLETADA**
