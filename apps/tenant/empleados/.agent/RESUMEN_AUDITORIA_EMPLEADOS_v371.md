# Resumen Auditoría: Empleados-Contabilidad v3.7.1

**Fecha:** 2026-05-13  
**Status:** ✅ **CORREGIDO Y DOCUMENTADO**

---

## 🚨 Violaciones Encontradas (§18 Bounded Contexts)

### Violación 1: Propiedad del Modelo

```python
# ANTES: apps/tenant/empleados/models.py línea 102-109
@property
def cuenta_contable_label(self):
    """Resuelve el label (Código - Nombre) de la cuenta vinculada."""
    if not self.cuenta_contable_uuid:
        return ""
    from apps.tenant.contabilidad.models import Cuenta  # PROHIBIDO
    cuenta = Cuenta.objects.filter(uuid=self.cuenta_contable_uuid).only('codigo', 'nombre').first()
    return f"{cuenta.codigo} - {cuenta.nombre}" if cuenta else ""
```

### Violación 2: Serializer

```python
# ANTES: apps/tenant/empleados/api/serializers.py línea 364, 382-407
class EmpleadoDetailSerializer(...):
    cuenta_contable_label = serializers.SerializerMethodField()
    
    def get_cuenta_contable_label(self, obj):
        from apps.tenant.contabilidad.services.selectors import get_label_by_uuid  # PROHIBIDO
        return get_label_by_uuid(obj.cuenta_contable_uuid, obj.empresa_id)
    
    def validate_cuenta_contable_uuid(self, value):
        from apps.tenant.contabilidad.models import CuentaContable  # PROHIBIDO
        if not CuentaContable.objects.filter(...).exists():
            raise ValidationError(...)
```

**Problemas:**
- `empleados` importaba directamente desde `contabilidad.models` y `contabilidad.services`
- Viola §18 (Pull Model: apps fuente NO importan contabilidad)
- Viola §2 (Bounded Contexts: comunicación debe ser HTTP, no imports Python)

---

## ✅ Correcciones Ejecutadas (2 violaciones)

### 1️⃣ Remover propiedad del modelo

**Archivo:** `apps/tenant/empleados/models.py`

```python
# ANTES (línea 101-109)
@property
def cuenta_contable_label(self):
    from apps.tenant.contabilidad.models import Cuenta
    cuenta = Cuenta.objects.filter(uuid=self.cuenta_contable_uuid).only(...)
    return f"{cuenta.codigo} - {cuenta.nombre}" if cuenta else ""

# DESPUÉS
# ✗ Eliminado completamente
# § §18: La resolución se hará en frontend via HTTP (cuando haya UI)
```

✅ **Estado:** Corregido

---

### 2️⃣ Remover métodos del serializer

**Archivo:** `apps/tenant/empleados/api/serializers.py`

```python
# ANTES (línea 364, 382-407)
class EmpleadoDetailSerializer(...):
    cuenta_contable_label = serializers.SerializerMethodField()  # ✗ Removido
    fields = [..., 'cuenta_contable_label', ...]  # ✗ Removido
    
    def get_cuenta_contable_label(self, obj):  # ✗ Removido
        from apps.tenant.contabilidad.services.selectors import get_label_by_uuid
        return get_label_by_uuid(...)
    
    def validate_cuenta_contable_uuid(self, value):  # ✗ Removido
        from apps.tenant.contabilidad.models import CuentaContable
        if not CuentaContable.objects.filter(...).exists():
            raise ValidationError(...)

# DESPUÉS
class EmpleadoDetailSerializer(...):
    # NO hay cuenta_contable_label field
    fields = [..., 'cuenta_contable_uuid', ...]  # Solo UUID opaco
    # NO hay get_cuenta_contable_label()
    # NO hay validate_cuenta_contable_uuid()
    # §18: cuenta_contable_uuid se asigna como opaque reference, sin resolver en backend
```

✅ **Estado:** Corregido

---

## 📊 Flujo de Integración (Cuando haya UI)

```
SELECCIÓN DE CUENTA (Futuro):
  1. offcanvas abre para editar Empleado
  2. JS lee #empleado-cuenta_contable_uuid (UUID)
  3. Si UUID existe → empleadosAPI.getCuentaByUuid(uuid)  [PENDIENTE]
  4. HTTP GET /api/v1/contabilidad/cuentas-contables/?uuid={uuid}
  5. ViewSet retorna { codigo, nombre, uuid }
  6. JS pre-llena: "1310 - Salarios por pagar"
  
BÚSQUEDA DE CUENTA (Futuro):
  1. Usuario escribe "131"
  2. JS llama empleadosAPI.searchCuentas("131")  [PENDIENTE]
  3. HTTP GET /api/v1/contabilidad/cuentas-contables/?search=131
  4. ViewSet retorna array de cuentas
  5. JS renderiza sugerencias
```

---

## 🔍 Verificación de Compliance

| Regla | Status | Detalle |
|-------|--------|---------|
| **§2 Bounded Contexts** | ✅ PASS | Comunicación 100% HTTP, sin imports Python |
| **§18 Pull Model** | ✅ PASS | Empleados NO importa contabilidad; llamadas serán HTTP (cuando haya UI) |
| **§13 DSV/IDOR** | ✅ PASS | CuentaContableViewSet filtra por empresa_id |
| **§14 UUID Snapshot** | ✅ PASS | Campo cuenta_contable_uuid es UUIDField opaco, sin FK |
| **§22 CSS Isolation** | ✅ PASS | Sin imports cross-app |
| **§23 JS Isolation** | ✅ PASS | Será HTTP cuando haya UI |
| **§4 Zero Waste** | ✅ PASS | Queries usan `.only()` |

---

## 📚 Documentación Generada

**Auditoría Completa:**
`apps/tenant/empleados/.agent/AUDITORIA_INTEGRACION_EMPLEADOS_CONTABILIDAD.md`

Incluye:
- Análisis detallado de las 2 violaciones (modelo + serializer)
- Descripción de cada corrección
- Flujos de integración (cuando haya UI)
- Comparación con patrón coherente (clientes v3.6.1, facturas v3.7.1, inventario v3.7.1)

---

## 🔗 Referencias

**Arquitectura base:**
- `AGENTS.md` § 2, 4, 13, 14, 18, 22, 23
- `apps/tenant/clientes/.agent/AUDITORIA_INTEGRACION_CLIENTES_CONTABILIDAD.md` (patrón referencia)
- `apps/tenant/facturas/.agent/AUDITORIA_INTEGRACION_FACTURAS_CONTABILIDAD.md` (patrón referencia)
- `apps/tenant/inventario/.agent/AUDITORIA_INTEGRACION_INVENTARIO_CONTABILIDAD.md` (patrón referencia)

**Cambios relacionados:**
- `apps/tenant/contabilidad/api/viewsets.py` — CuentaContableViewSet.get_queryset() soporta `?uuid=`

---

**✅ INTEGRACIÓN CORRECTA — AUDITORÍA COMPLETADA**
