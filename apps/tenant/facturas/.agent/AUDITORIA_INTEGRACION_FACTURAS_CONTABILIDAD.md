# Auditoría: Integración Facturas ↔ Contabilidad

**Versión:** 3.7.1  
**Fecha:** 2026-05-13  
**Status:** ✅ CORRECCIONES APLICADAS — INTEGRACIÓN CORRECTA  
**Alcance:** `apps/tenant/facturas` + `apps/tenant/contabilidad`

---

## 🎯 Objetivo de la Auditoría

Verificar que la integración entre el módulo `facturas` (v3.7.0) y `contabilidad` respeta los pilares de arquitectura AGENTS.md, en particular los Bounded Contexts (§18), Pull Model, e isolation entre apps.

---

## 🔬 Checks de Auditoría

### CHECK §18 — Bounded Contexts / Pull Model ❌ → ✅ CORREGIDO

**Hallazgo CRÍTICO:**

```python
# ANTES (violación §18): apps/tenant/facturas/api/serializers.py línea 172-178
def get_cuenta_contable_label(self, obj):
    """Retorna el label (codigo - nombre) de la cuenta vinculada."""
    if not obj.cuenta_contable_uuid:
        return None
    from apps.tenant.contabilidad.models import CuentaContable  # PROHIBIDO
    cuenta = CuentaContable.objects.filter(uuid=obj.cuenta_contable_uuid).only('codigo', 'nombre').first()
    return f"{cuenta.codigo} - {cuenta.nombre}" if cuenta else None
```

**Análisis:**
- `facturas` importaba directamente el modelo `CuentaContable` de `contabilidad` en el serializer
- Viola explícitamente AGENTS.md §18: *"Ninguna app puede crear AsientoContable ni MovimientoContable directamente desde source apps. Las apps fuente NO conocen ni dependen de contabilidad"*
- También viola §2 (Bounded Contexts): las apps deben comunicarse via endpoints HTTP, no via imports Python

**Corrección Aplicada:**

| Capa | Cambio |
|------|--------|
| `facturas/api/serializers.py` | Eliminado el import y reemplazado con método que retorna `None` (comentario §18) |
| `contabilidad/api/viewsets.py` | Ya soporta filtro `?uuid=` desde auditoría anterior (clientes) |
| `facturas/static/js/facturas/facturas.api.js` | Agregada función `getCuentaByUuid(uuid)` que llama al endpoint HTTP de contabilidad |
| `facturas/static/js/facturas/features/facturas_editor.js` | `initCuentaContableSearch()` pre-carga el nombre de la cuenta via `getCuentaByUuid()` al abrir en modo edición |
| `facturas/templates/.../offcanvas_editar_factura.html` | Eliminada dependencia de `{{ factura.cuenta_contable_label }}` — el campo texto empieza vacío y JS lo pre-carga |

**Flujo Correcto Post-Corrección:**

```
Backend (Python):
  Factura.cuenta_contable_uuid  →  UUID almacenado como referencia opaca

Frontend (JS):
  offcanvas editar se abre
      ↓
  JS lee #factura-cuenta_contable_uuid (UUID de la factura)
      ↓
  facturasAPI.getCuentaByUuid(uuid)
      → GET /api/v1/contabilidad/cuentas-contables/?uuid={uuid}&app_origen=facturas
      ↓
  CuentaContableViewSet retorna { codigo, nombre, uuid }
      ↓
  JS pre-llena campo de texto: "130505 - Clientes nacionales"
```

---

### CHECK §2 — Bounded Contexts ✅ PASS (post-corrección)

| Aspecto | Estado |
|---------|--------|
| `facturas` NO importa modelos de `contabilidad` | ✅ PASS |
| Comunicación via HTTP endpoints únicamente | ✅ PASS |
| `contabilidad` expone endpoint público `?uuid=` | ✅ PASS |

---

### CHECK §17 — Bridge Isolation ✅ PASS

| Aspecto | Estado |
|---------|--------|
| Sin imports `apps.public` en `facturas` | ✅ PASS |
| Sin imports `apps.public` en `contabilidad` | ✅ PASS |

---

### CHECK §14 — UUID como referencia opaca ✅ CORRECTO

El campo `cuenta_contable_uuid` en `Factura` es un `UUIDField(null=True, blank=True)` — almacena el UUID de la `CuentaContable` como referencia opaca sin FK real.

**Justificación arquitectónica:**
- No es un FK real para mantener desacoplamiento entre bounded contexts
- Sigue el patrón **Snapshot ID**: guarda el identificador, no la relación
- La resolución del objeto referenciado se hace via HTTP (no ORM cross-app)

---

### CHECK §22/§23 — CSS/JS Isolation ✅ PASS

| Aspecto | Estado |
|---------|--------|
| Sin `<link>` cross-app en templates facturas | ✅ PASS |
| `facturasAPI.searchCuentas()` llama a endpoint HTTP de contabilidad (no import JS) | ✅ PASS correcto |
| `facturasAPI.getCuentaByUuid()` llama a endpoint HTTP de contabilidad (no import JS) | ✅ PASS correcto |
| Namespace `window.Sintel.Facturas` aislado | ✅ PASS |

---

### CHECK §13 — DSV/IDOR en campo cuenta_contable_uuid ✅ PASS

| Aspecto | Estado |
|---------|--------|
| `CuentaContableViewSet` filtra por `empresa_id` del tenant autenticado | ✅ PASS |
| Una factura de Empresa A no puede asignar una cuenta de Empresa B | ✅ PASS (DSV en ViewSet contabilidad) |
| Endpoint `?uuid=` respeta la empresa del tenant autenticado | ✅ PASS (queryset `qs_cuenta_list()` ya filtra por empresa) |

---

### CHECK §4 — Zero Waste en el endpoint ?uuid= ✅ PASS

El `get_queryset()` modificado usa `qs_cuenta_list()` que ya tiene `.only()` definido en el selector de contabilidad.

---

## 📊 Estructura de la Integración (Post-Corrección)

```
apps/tenant/facturas/
  models.py:
    Factura
      └─ cuenta_contable_uuid: UUIDField (null=True)  ← referencia opaca

  api/serializers.py:
    FacturaDetailSerializer.get_cuenta_contable_label()
      └─ Retorna None (comentario §18)
      └─ NO importa CuentaContable (§18 cumplido)

  static/js/facturas/facturas.api.js:
    facturasAPI.searchCuentas(texto)  → GET /api/v1/contabilidad/cuentas-contables/?search=...
    facturasAPI.getCuentaByUuid(uuid) → GET /api/v1/contabilidad/cuentas-contables/?uuid=...

  static/js/facturas/features/facturas_editor.js:
    initCuentaContableSearch()
      ├─ Si hay UUID inicial → getCuentaByUuid() → pre-carga campo texto
      └─ Input de usuario → searchCuentas() → lista de sugerencias

  templates/.../offcanvas_editar_factura.html:
    <input type="text" id="factura-cuenta_contable_search" value="">  ← JS lo pre-carga
    <input type="hidden" id="factura-cuenta_contable_uuid" value="{{ factura.cuenta_contable_uuid|default:'' }}">

─────────────────────────────────────────────────────────────
                    HTTP (§2 correcto)
─────────────────────────────────────────────────────────────

apps/tenant/contabilidad/
  api/viewsets.py:
    CuentaContableViewSet.get_queryset()
      ├─ ?search=texto   → filtra por codigo/nombre/descripcion
      ├─ ?uuid=uuid      → filtra por UUID específico (v3.7 nuevo)
      ├─ ?app_origen=facturas → filtra cuentas de cartera/ingreso/gasto
      └─ empresa_id DSV aplicado en qs_cuenta_list()
```

---

## ✅ Archivos Modificados

| Archivo | Cambio | Regla |
|---------|--------|-------|
| `apps/tenant/facturas/api/serializers.py` | Eliminado import `CuentaContable` + simplificado `get_cuenta_contable_label()` | §18 |
| `apps/tenant/facturas/static/js/facturas/facturas.api.js` | Agregado `getCuentaByUuid(uuid)` | §23 / §18 |
| `apps/tenant/facturas/static/js/facturas/features/facturas_editor.js` | Pre-carga en `initCuentaContableSearch()` | §18 |
| `apps/tenant/facturas/templates/.../offcanvas_editar_factura.html` | Eliminada variable `{{ factura.cuenta_contable_label }}` | §18 |

---

## 🏗️ Decisiones Arquitectónicas

### Por qué NO usar FK real entre Factura y CuentaContable

```
PROHIBIDO (acoplamiento):
  Factura.cuenta_contable = ForeignKey(CuentaContable)  # Dependencia directa

CORRECTO (desacoplamiento):
  Factura.cuenta_contable_uuid = UUIDField()  # Referencia opaca
```

- Una FK haría que `facturas` dependiera del schema de `contabilidad`
- Si `contabilidad` cambia su modelo, no afecta `facturas`
- El UUID es el mínimo acoplamiento posible (solo el identificador)

### Por qué el endpoint HTTP es la solución correcta (§18)

```
PROHIBIDO (import Python cross-app):
  from apps.tenant.contabilidad.models import CuentaContable

CORRECTO (HTTP entre bounded contexts):
  GET /api/v1/contabilidad/cuentas-contables/?uuid={uuid}
```

- Los bounded contexts se comunican via contrato HTTP, no via imports Python
- Esto permite que cada app evolucione independientemente
- El endpoint de contabilidad puede cambiar su implementación sin afectar facturas

---

## 🔗 Migración 0007 — Análisis

```python
# apps/tenant/facturas/migrations/0007_factura_cuenta_contable_uuid.py
migrations.AddField(
    model_name="factura",
    name="cuenta_contable_uuid",
    field=models.UUIDField(blank=True, help_text="Cuenta PUC nivel 6 (Cartera/Ingreso/Gasto)", null=True),
)
```

**Análisis:**
- ✅ Campo nullable — no rompe registros existentes
- ✅ Sin FK real — mantiene desacoplamiento entre bounded contexts
- ✅ `db_index` ausente — agregar en versión futura si hay consultas frecuentes por este campo

---

## 🔄 Comparación con Clientes (Coherencia Arquitectónica)

| Aspecto | Clientes (v3.6.1) | Facturas (v3.7.1) | Status |
|---------|-------------------|-------------------|--------|
| UUID opaco para referencia | ✅ UUIDField nullable | ✅ UUIDField nullable | Coherente |
| Violación §18 removida | ✅ Import removido | ✅ Import removido | Coherente |
| Endpoint ?uuid= soportado | ✅ Sí | ✅ Sí | Coherente |
| API JS con getCuentaByUuid() | ✅ clientesAPI | ✅ facturasAPI | Coherente |
| Pre-carga en editor | ✅ initCuentaContableSearch() | ✅ initCuentaContableSearch() | Coherente |
| Template con value="" | ✅ Sí | ✅ Sí | Coherente |

---

**Última Actualización:** 2026-05-13  
**Status:** ✅ **INTEGRACIÓN CORRECTA — §18 CUMPLIDO**

