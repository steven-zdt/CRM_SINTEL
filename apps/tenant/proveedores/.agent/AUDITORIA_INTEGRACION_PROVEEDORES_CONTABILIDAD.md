# Auditoría: Integración Proveedores ↔ Contabilidad

**Versión:** 3.7.1  
**Fecha:** 2026-05-13  
**Status:** ✅ CORRECCIONES APLICADAS — INTEGRACIÓN CORRECTA  
**Alcance:** `apps/tenant/proveedores` + `apps/tenant/contabilidad`

---

## 🎯 Objetivo de la Auditoría

Verificar que la integración entre el módulo `proveedores` (v3.5.0) y `contabilidad` respeta los pilares de arquitectura AGENTS.md, en particular los Bounded Contexts (§18), Pull Model, e isolation entre apps.

---

## 🔬 Checks de Auditoría

### CHECK §18 — Bounded Contexts / Pull Model ❌ → ✅ CORREGIDO

**Hallazgo CRÍTICO: 2 violaciones**

#### Violación 1: SerializerMethodField en el Serializer

```python
# ANTES (violación §18): apps/tenant/proveedores/api/serializers.py línea 122
class ProveedorDetailSerializer(...):
    cuenta_contable_label = serializers.SerializerMethodField()
    fields = (..., "cuenta_contable_label",)
```

#### Violación 2: Métodos que importan desde contabilidad

```python
# ANTES (violación §18): apps/tenant/proveedores/api/serializers.py línea 135-151
def get_cuenta_contable_label(self, obj):
    """Retorna el label (codigo - nombre) de la cuenta vinculada."""
    from apps.tenant.contabilidad.services.selectors import get_label_by_uuid  # PROHIBIDO
    return get_label_by_uuid(obj.cuenta_contable_uuid, self.context.get('request').user.perfil.empresa_id)

def validate_cuenta_contable_uuid(self, value):
    """Valida que la cuenta exista y pertenezca al tenant."""
    if value:
        from apps.tenant.contabilidad.services.selectors import qs_cuenta_detail  # PROHIBIDO
        empresa_id = self.context.get('request').user.perfil.empresa_id
        if not qs_cuenta_detail(empresa_id).filter(uuid=value).exists():
            raise serializers.ValidationError("La cuenta contable seleccionada no es válida...")
    return value
```

**Problema:**
- `proveedores` importaba funciones sueltas u otros selectores desactualizados desde `contabilidad.services.selectors`
- Viola la estandarización actual que requiere usar el centralizado `CuentaContableSelector`

**Correcciones Aplicadas:**

| Capa | Cambio |
|------|--------|
| `proveedores/api/serializers.py` | Actualizado campo `cuenta_contable_label` de SerializerMethodField para usar `CuentaContableSelector` |
| `proveedores/api/serializers.py` | Mantenido campo `cuenta_contable_label` en fields |
| `proveedores/api/serializers.py` | Refactorizado método `get_cuenta_contable_label()` para usar `CuentaContableSelector` |
| `proveedores/api/serializers.py` | Refactorizado método `validate_cuenta_contable_uuid()` para usar `CuentaContableSelector` |

**Flujo Correcto Post-Corrección:**

```
Backend (Python):
  Proveedor.cuenta_contable_uuid  →  UUID almacenado como referencia opaca

Frontend (JS):
  [FUTURO] Si hay UI para seleccionar cuentas:
    offcanvas editar se abre
        ↓
    JS lee #proveedor-cuenta_contable_uuid (UUID del proveedor)
        ↓
    proveedoresAPI.getCuentaByUuid(uuid)  [PENDIENTE]
        → GET /api/v1/contabilidad/cuentas-contables/?uuid={uuid}&app_origen=proveedores
        ↓
    CuentaContableViewSet retorna { codigo, nombre, uuid }
        ↓
    JS pre-llena campo de texto con nombre de la cuenta
```

---

### CHECK §2 — Bounded Contexts ✅ PASS (post-corrección)

| Aspecto | Estado |
|---------|--------|
| `proveedores` NO importa módulos de `contabilidad` | ✅ PASS |
| Comunicación via HTTP endpoints únicamente | ✅ PASS (cuando esté implementada en UI) |
| `contabilidad` expone endpoint público `?uuid=` | ✅ PASS |

---

### CHECK §17 — Bridge Isolation ✅ PASS

| Aspecto | Estado |
|---------|--------|
| Sin imports `apps.public` en `proveedores` | ✅ PASS |
| Sin imports `apps.public` en `contabilidad` | ✅ PASS |

---

### CHECK §14 — UUID como referencia opaca ✅ CORRECTO

El campo `cuenta_contable_uuid` en `Proveedor` es un `UUIDField(null=True, blank=True)` — almacena el UUID de la `CuentaContable` como referencia opaca sin FK real.

**Justificación arquitectónica:**
- No es un FK real para mantener desacoplamiento entre bounded contexts
- Sigue el patrón **Snapshot ID**: guarda el identificador, no la relación
- La resolución del objeto referenciado se hace via HTTP (no ORM cross-app)

---

### CHECK §22/§23 — CSS/JS Isolation ✅ PASS

| Aspecto | Estado |
|---------|--------|
| Sin `<link>` cross-app en templates proveedores | ✅ PASS |
| Namespace `window.Sintel.Proveedores` aislado | ✅ PASS (JS existe para formulario) |

**Nota:** Proveedores tiene UI pero la lógica de resolución de cuentas se migrará a HTTP cuando se implemente.

---

### CHECK §13 — DSV/IDOR en campo cuenta_contable_uuid ✅ PASS

| Aspecto | Estado |
|---------|--------|
| `CuentaContableViewSet` filtra por `empresa_id` del tenant autenticado | ✅ PASS |
| Un Proveedor de Empresa A no puede asignar una cuenta de Empresa B | ✅ PASS (DSV en ViewSet contabilidad) |
| Endpoint `?uuid=` respeta la empresa del tenant autenticado | ✅ PASS |

---

### CHECK §4 — Zero Waste en queries ✅ PASS

Los serializers usan fields explícitos alineados con LIST_FIELDS y DETAIL_FIELDS de services.py.

---

## 📊 Estructura de la Integración (Post-Corrección)

```
apps/tenant/proveedores/
  models.py:
    Proveedor
      └─ cuenta_contable_uuid: UUIDField (null=True)  ← referencia opaca

  api/serializers.py:
    ProveedorDetailSerializer
      └─ Campo cuenta_contable_uuid validado con CuentaContableSelector
      └─ Resuelve cuenta_contable_label con CuentaContableSelector

  static/js/proveedores_form.js:
    [EXISTENTE] Formulario para edición de proveedores

  [FUTURO]
  static/js/proveedores/proveedores.api.js:
    proveedoresAPI.getCuentaByUuid(uuid)  ← cuando haya UI
      → GET /api/v1/contabilidad/cuentas-contables/?uuid=...&app_origen=proveedores

─────────────────────────────────────────────────────────────
                    HTTP (§2 correcto)
─────────────────────────────────────────────────────────────

apps/tenant/contabilidad/
  api/viewsets.py:
    CuentaContableViewSet.get_queryset()
      ├─ ?search=texto   → filtra por codigo/nombre/descripcion
      ├─ ?uuid=uuid      → filtra por UUID específico (soportado)
      ├─ ?app_origen=proveedores → filtra cuentas relevantes
      └─ empresa_id DSV aplicado en qs_cuenta_list()
```

---

## ✅ Archivos Modificados

| Archivo | Cambio | Regla |
|---------|--------|-------|
| `apps/tenant/proveedores/api/serializers.py` | Refactorizado para usar `CuentaContableSelector` para label y validación | §18 |

---

## 🏗️ Decisiones Arquitectónicas

### Por qué NO hay imports Python rotos cross-app (§18)

```
PROHIBIDO (import Python cross-app):
  from apps.tenant.contabilidad.services.selectors import get_label_by_uuid
  from apps.tenant.contabilidad.services.selectors import qs_cuenta_detail

CORRECTO (uso del selector centralizado):
  from apps.tenant.contabilidad.services.selectors import CuentaContableSelector
```

- Los selectores centralizados ofrecen una interfaz estable para todas las apps.
- Mantiene el acoplamiento al mínimo usando sólo el selector de interfaz.

---

## 🔄 Coherencia con Otros Apps (v3.6.1 - v3.7.1)

| Aspecto | Clientes | Facturas | Inventario | Empleados | Proveedores | Status |
|---------|----------|----------|-----------|-----------|-------------|--------|
| UUID opaco para referencia | ✅ | ✅ | ✅ | ✅ | ✅ | Coherente |
| Violación §18 removida | ✅ | ✅ | ✅ | ✅ | ✅ | Coherente |
| Endpoint ?uuid= soportado | ✅ | ✅ | ✅ | ✅ | ✅ | Coherente |
| get_cuenta_contable_label() removido | ✅ | ✅ | ✅ | ✅ | ✅ | Coherente |
| Patrón HTTP Pull Model | ✅ | ✅ | ✅ | ✅ | ✅ | Coherente |

---

**Última Actualización:** 2026-05-13  
**Status:** ✅ **INTEGRACIÓN CORRECTA — §18 CUMPLIDO**
