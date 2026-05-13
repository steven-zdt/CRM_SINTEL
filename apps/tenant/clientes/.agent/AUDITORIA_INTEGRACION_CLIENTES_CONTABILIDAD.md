# Auditoría: Integración Clientes ↔ Contabilidad

**Versión:** 3.6.1  
**Fecha:** 2026-05-11  
**Status:** ✅ CORRECCIONES APLICADAS — INTEGRACIÓN CORRECTA  
**Alcance:** `apps/tenant/clientes` + `apps/tenant/contabilidad`

---

## 🎯 Objetivo de la Auditoría

Verificar que la integración entre el módulo `clientes` (v3.5.0) y `contabilidad` respeta los pilares de arquitectura AGENTS.md, en particular los Bounded Contexts (§18), Pull Model, e isolation entre apps.

---

## 🔬 Checks de Auditoría

### CHECK §18 — Bounded Contexts / Pull Model ❌ → ✅ CORREGIDO

**Hallazgo CRÍTICO:**

```python
# ANTES (violación §18): apps/tenant/clientes/api/viewsets.py línea 393
from apps.tenant.contabilidad.models import CuentaContable   # PROHIBIDO
cuenta = CuentaContable.objects.filter(uuid=..., empresa_id=...).only(...)
```

**Análisis:**
- `clientes` importaba directamente el modelo `CuentaContable` de `contabilidad`
- Viola explícitamente AGENTS.md §18: *"Ninguna app puede crear AsientoContable ni MovimientoContable directamente desde source apps. Las apps fuente NO conocen ni dependen de contabilidad"*
- También viola §2 (Bounded Contexts): las apps deben comunicarse via endpoints HTTP, no via imports Python

**Corrección Aplicada:**

| Capa | Cambio |
|------|--------|
| `clientes/api/viewsets.py` | Eliminado el bloque `cuenta_info` con el import directo |
| `contabilidad/api/viewsets.py` | Agregado filtro `?uuid=` al `get_queryset()` de `CuentaContableViewSet` |
| `clientes/static/js/clientes.api.js` | Agregada función `getCuentaByUuid(uuid)` que llama al endpoint HTTP de contabilidad |
| `clientes/static/js/clientes.editor.js` | `initCuentaContableSearch()` pre-carga el nombre de la cuenta via `getCuentaByUuid()` al abrir en modo edición |
| `offcanvas_editar_cliente.html` | Eliminada dependencia de `{{ cuenta_info }}` — el campo texto empieza vacío y JS lo pre-carga |

**Flujo Correcto Post-Corrección:**

```
Backend (Python):
  Cliente.cuenta_contable_uuid  →  UUID almacenado como referencia opaca

Frontend (JS):
  offcanvas editar se abre
      ↓
  JS lee #cliente-cuenta_contable_uuid (UUID del cliente)
      ↓
  clientesAPI.getCuentaByUuid(uuid)
      → GET /api/v1/contabilidad/cuentas-contables/?uuid={uuid}&app_origen=clientes
      ↓
  CuentaContableViewSet retorna { codigo, nombre, uuid }
      ↓
  JS pre-llena campo de texto: "130505 - Clientes nacionales"
```

---

### CHECK §2 — Bounded Contexts ✅ PASS (post-corrección)

| Aspecto | Estado |
|---------|--------|
| `clientes` NO importa modelos de `contabilidad` | ✅ PASS |
| Comunicación via HTTP endpoints únicamente | ✅ PASS |
| `contabilidad` expone endpoint público `?uuid=` | ✅ PASS |

---

### CHECK §17 — Bridge Isolation ✅ PASS

| Aspecto | Estado |
|---------|--------|
| Sin imports `apps.public` en `clientes` | ✅ PASS |
| Sin imports `apps.public` en `contabilidad` | ✅ PASS |

---

### CHECK §14 — UUID como referencia opaca ✅ CORRECTO

El campo `cuenta_contable_uuid` en `Cliente` es un `UUIDField(null=True, blank=True)` — almacena el UUID de la `CuentaContable` como referencia opaca sin FK real.

**Justificación arquitectónica:**
- No es un FK real para mantener desacoplamiento entre bounded contexts
- Sigue el patrón **Snapshot ID**: guarda el identificador, no la relación
- La resolución del objeto referenciado se hace via HTTP (no ORM cross-app)

---

### CHECK §22/§23 — CSS/JS Isolation ✅ PASS

| Aspecto | Estado |
|---------|--------|
| Sin `<link>` cross-app en templates clientes | ✅ PASS |
| `clientesAPI.searchCuentas()` llama a endpoint HTTP de contabilidad (no import JS) | ✅ PASS correcto |
| `clientesAPI.getCuentaByUuid()` llama a endpoint HTTP de contabilidad (no import JS) | ✅ PASS correcto |
| Namespace `window.Sintel.Clientes` aislado | ✅ PASS |

---

### CHECK §13 — DSV/IDOR en campo cuenta_contable_uuid ✅ PASS

| Aspecto | Estado |
|---------|--------|
| `CuentaContableViewSet` filtra por `empresa_id` del tenant autenticado | ✅ PASS |
| Un cliente de Empresa A no puede asignar una cuenta de Empresa B | ✅ PASS (DSV en ViewSet contabilidad) |
| Endpoint `?uuid=` respeta la empresa del tenant autenticado | ✅ PASS (queryset `qs_cuenta_list()` ya filtra por empresa) |

---

### CHECK §4 — Zero Waste en el endpoint ?uuid= ✅ PASS

El `get_queryset()` modificado usa `qs_cuenta_list()` que ya tiene `.only()` definido en el selector de contabilidad.

---

## 📊 Estructura de la Integración (Post-Corrección)

```
apps/tenant/clientes/
  models.py:
    Cliente
      └─ cuenta_contable_uuid: UUIDField (null=True)  ← referencia opaca

  api/viewsets.py:
    render_offcanvas_editar()
      ├─ Pasa: cliente.cuenta_contable_uuid al contexto
      └─ NO importa CuentaContable (§18 cumplido)

  static/js/clientes.api.js:
    clientesAPI.searchCuentas(texto)  → GET /api/v1/contabilidad/cuentas-contables/?search=...
    clientesAPI.getCuentaByUuid(uuid) → GET /api/v1/contabilidad/cuentas-contables/?uuid=...

  static/js/clientes.editor.js:
    initCuentaContableSearch()
      ├─ Si hay UUID inicial → getCuentaByUuid() → pre-carga campo texto
      └─ Input de usuario → searchCuentas() → lista de sugerencias

  templates/.../offcanvas_editar_cliente.html:
    <input type="text" id="cuenta_contable_search" value="">  ← JS lo pre-carga
    <input type="hidden" id="cuenta_contable_uuid" value="{{ cliente.cuenta_contable_uuid }}">

─────────────────────────────────────────────────────────────
                    HTTP (§2 correcto)
─────────────────────────────────────────────────────────────

apps/tenant/contabilidad/
  api/viewsets.py:
    CuentaContableViewSet.get_queryset()
      ├─ ?search=texto   → filtra por codigo/nombre/descripcion
      ├─ ?uuid=uuid      → filtra por UUID específico (v3.6.1 nuevo)
      ├─ ?app_origen=clientes → filtra cuentas de cartera
      └─ empresa_id DSV aplicado en qs_cuenta_list()
```

---

## ✅ Archivos Modificados

| Archivo | Cambio | Regla |
|---------|--------|-------|
| `apps/tenant/clientes/api/viewsets.py` | Eliminado import `CuentaContable` + bloque `cuenta_info` | §18 |
| `apps/tenant/contabilidad/api/viewsets.py` | Agregado filtro `?uuid=` en `get_queryset()` | §2 (exponiendo endpoint HTTP) |
| `apps/tenant/clientes/static/js/clientes.api.js` | Agregado `getCuentaByUuid(uuid)` | §23 / §18 |
| `apps/tenant/clientes/static/js/clientes.editor.js` | Pre-carga en `initCuentaContableSearch()` | §18 |
| `apps/tenant/clientes/templates/.../offcanvas_editar_cliente.html` | Eliminada variable `{{ cuenta_info }}` | §18 |

---

## 🏗️ Decisiones Arquitectónicas

### Por qué NO usar FK real entre Cliente y CuentaContable

```
PROHIBIDO (acoplamiento):
  Cliente.cuenta_contable = ForeignKey(CuentaContable)  # Dependencia directa

CORRECTO (desacoplamiento):
  Cliente.cuenta_contable_uuid = UUIDField()  # Referencia opaca
```

- Una FK haría que `clientes` dependiera del schema de `contabilidad`
- Si `contabilidad` cambia su modelo, no afecta `clientes`
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
- El endpoint de contabilidad puede cambiar su implementación sin afectar clientes

---

## 🔗 Migración 0004 — Análisis

```python
# apps/tenant/clientes/migrations/0004_cliente_cuenta_contable_uuid_and_more.py
migrations.AddField(
    model_name="cliente",
    name="cuenta_contable_uuid",
    field=models.UUIDField(blank=True, help_text="Cuenta PUC nivel 6 (Cartera)", null=True),
)
```

**Análisis:**
- ✅ Campo nullable — no rompe registros existentes
- ✅ Sin FK real — mantiene desacoplamiento entre bounded contexts
- ✅ `db_index` ausente — agregar en versión futura si hay consultas frecuentes por este campo

---

**Última Actualización:** 2026-05-11  
**Status:** ✅ **INTEGRACIÓN CORRECTA — §18 CUMPLIDO**
