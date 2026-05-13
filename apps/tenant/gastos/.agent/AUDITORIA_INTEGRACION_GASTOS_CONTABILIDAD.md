# Auditoría: Integración Gastos ↔ Contabilidad

**Versión:** 3.7.1  
**Fecha:** 2026-05-13  
**Status:** ✅ IMPLEMENTADO — INTEGRACIÓN §18 COMPLIANT  
**Alcance:** `apps/tenant/gastos` + `apps/tenant/contabilidad`

---

## 🎯 Objetivo de la Auditoría

Verificar que el módulo `gastos` (v2.62) expone un campo UUID opaco para la cuenta de gasto sin violar §18 (Pull Model), permitiendo que `contabilidad` extraiga información y **orqueste la determinación de la cuenta de contrapartida** según reglas contables.

---

## 📋 Contexto Arquitectónico

El modelo `DocumentoSoporte` en `gastos` registra egresos del tenant. Para integración contable:

| Responsabilidad | Componente | Campo |
|---|---|---|
| **App Gastos** | DocumentoSoporte | `cuenta_gasto_uuid` (opaco) |
| **App Contabilidad** | Extractor + Orquestador | Determina contrapartida |

**Arquitectura Pull Model (§18):**
- Apps source **NO importan** contabilidad
- Apps source **NO deciden** contrapartidas
- Contabilidad **orquesta** toda la lógica contable

---

## ✅ Implementación (v3.7.1)

### 1. Modelos — `models.py` ✅

**Estado:** Campo UUID único (2026-05-13)

```python
# Líneas 188-191
cuenta_gasto_uuid = models.UUIDField(
    null=True, blank=True, db_index=True,
    verbose_name="Cuenta de Gasto/Egreso (UUID)",
    help_text="UUID de CuentaContable de resultado. Contabilidad determina contrapartida."
)
```

**Compliance:** ✅ Opaco (sin FK), sin imports contabilidad.

---

### 2. Migración — `migrations/0014_remove_cuenta_contrapartida_uuid.py` ✅

**Estado:** Nueva migración (2026-05-13)

```python
operations = [
    migrations.RemoveField(
        model_name='documentosoporte',
        name='cuenta_contrapartida_uuid',
    ),
]
```

**Rationale:** Contrapartida NO es responsabilidad de gastos.

---

### 3. Selectors — `services/selectors.py` ✅

**Estado:** Campo único en field tuples

```python
DOCUMENTO_LIST_FIELDS = (
    'id', 'consecutivo', 'fecha', 'total', ...
    'cuenta_gasto_uuid'  # ✅ Solo cuenta de gasto
)

DOCUMENTO_DETAIL_FIELDS = (
    'id', 'consecutivo', 'fecha', ...
    'cuenta_gasto_uuid'  # ✅ Solo cuenta de gasto
)
```

**Compliance:** ✅ Zero Waste — campos en SSoT.

---

### 4. Serializers — `api/serializers.py` ✅

**Status:** Actualizado 2026-05-13

#### DocumentoSoporteListSerializer
```python
cuenta_gasto_uuid = serializers.UUIDField(allow_null=True, read_only=True)

fields = (..., 'cuenta_gasto_uuid')
```

#### DocumentoSoporteDetailSerializer
```python
cuenta_gasto_uuid = serializers.UUIDField(allow_null=True, required=False)

fields = (..., 'cuenta_gasto_uuid')
```

**Compliance:**
- ✅ NO hay imports de `contabilidad.services.selectors`
- ✅ NO hay `SerializerMethodField` resolviendo contrapartidas
- ✅ UUID opaco de gasto únicamente
- ✅ §18 Pull Model cumplido

---

### 5. Templates — Offcanvas Crear/Editar ✅

**Archivos:** 
- `offcanvas_crear_gasto.html`
- `offcanvas_editar_gasto.html`

#### Nueva Sección: Integración Contable (v3.7.1)

```html
{# Sección: Integración Contable (v3.7.1) - §18 Pull Model #}
<div class="mb-4">
    <h6 class="text-success border-bottom pb-2 mb-3">
        <i class="bi bi-calculator me-2"></i>Integración Contable
    </h6>
    <div class="mb-3">
        <label for="cuenta_gasto_uuid" class="form-label">Cuenta de Gasto/Egreso</label>
        <input type="hidden" id="cuenta_gasto_uuid" name="cuenta_gasto_uuid">
        <input type="text" class="form-control" id="cuenta_gasto_display" readonly>
        <small class="form-text text-muted">Contabilidad determinará la contrapartida automáticamente</small>
    </div>
</div>
```

**Patrón:** Input hidden almacena UUID único (gasto). Contrapartida determinada por contabilidad.

---

### 6. JavaScript — `gasto_editor.js` ✅

**Status:** Actualizado 2026-05-13

#### Función `collectData()` (v3.7.1)

```javascript
function collectData(form) {
    const gastoUuidVal = form.querySelector('#cuenta_gasto_uuid')?.value;

    return {
        documento_soporte: {
            // ... campos existentes ...
            cuenta_gasto_uuid: gastoUuidVal || null
            // NO envía contrapartida
        }
    };
}
```

**Compliance:** ✅ Captura UUID de gasto, contabilidad orquesta contrapartida.

---

## 🔍 Verificación de Compliance

| Regla | Status | Detalle |
|-------|--------|---------|
| **§2 Bounded Contexts** | ✅ PASS | Gastos NO importa contabilidad; comunicación será HTTP |
| **§18 Pull Model** | ✅ PASS | UUID opaco en serializers, sin resolución backend |
| **Orquestación** | ✅ PASS | Contrapartida = responsabilidad contabilidad |
| **§13 DSV/IDOR** | ✅ PASS | Campos empresa_id en selectors, filtrado por tenant |
| **§14 UUID Snapshot** | ✅ PASS | UUIDField opaco, sin FK, sin ORM cross-app |
| **§22/§23 CSS/JS Isolation** | ✅ PASS | Sin imports cross-app, JS namespace aislado |
| **§4 Zero Waste** | ✅ PASS | Campos en LIST_FIELDS/DETAIL_FIELDS, `.only()` en selectors |

---

## 🔗 Patrón Coherente (v3.7.1 — Arquitectura Orquestada)

| App | Campo Principal | Contrapartida | Status | §18 |
|-----|-----------------|---------------|--------|-----|
| Clientes | ✅ cuenta_contable_uuid | Contabilidad (futuro) | ✅ | ✅ |
| Facturas | ✅ cuenta_contable_uuid | Contabilidad (futuro) | ✅ | ✅ |
| Inventario | ✅ 3x UUID | Contabilidad (futuro) | ✅ | ✅ |
| Empleados | ✅ cuenta_contable_uuid | Contabilidad (futuro) | ✅ | ✅ |
| Proveedores | ✅ cuenta_contable_uuid | Contabilidad (futuro) | ✅ | ✅ |
| **Gastos** | ✅ cuenta_gasto_uuid | Contabilidad (orquesta) | ✅ | ✅ |

**Conclusión:** Patrón completamente consistente. **Todas 6 apps**: campo principal opaco, **contrapartida = responsabilidad contabilidad**.

---

## 🏗️ Decisiones Arquitectónicas

### Por qué NO hay campo de contrapartida en gastos

```python
# ❌ PROHIBIDO (violaría §18 + responsabilidad):
class DocumentoSoporte:
    cuenta_contrapartida_uuid = UUIDField()  # ← Gastos decide contrapartida

# ✅ CORRECTO (§18 + orquestación):
class DocumentoSoporte:
    cuenta_gasto_uuid = UUIDField()
    # Contrapartida determinada por contabilidad según:
    # - Tipo de transacción (gasto, inversión, pago, etc.)
    # - Reglas fiscales
    # - Políticas contables
```

**Razones:**
1. **Separación de responsabilidades:** Gastos → datos | Contabilidad → orquestación
2. **Flexibilidad:** Si reglas de contrapartida cambian, solo cambia contabilidad
3. **Coherencia:** Todas las apps siguen patrón idéntico
4. **Escalabilidad:** Contabilidad es el único "orquestador"

---

## 📊 Integración Futura (Cuando Haya Extractor)

```
ExtractorGastos (en contabilidad):
  1. Lee DocumentoSoporte.cuenta_gasto_uuid
  2. Aplica reglas contables para determinar contrapartida
  3. Mapea a TransaccionEconomica con ambas cuentas
  4. Contabilizador genera asientos automáticos
  
Ejemplo:
  Gasto = 5105 (Gastos de Personal)
  ExtractorGastos.aplicar_reglas() → Contrapartida = 1110 (Bancos) o 2205 (CxP)
```

---

## ✅ Archivos Modificados (v3.7.1)

| Archivo | Cambios | Regla |
|---------|---------|-------|
| `models.py` | Removido campo contrapartida | §18 |
| `migrations/0014_*.py` | Nueva migración (RemoveField) | §18 |
| `api/serializers.py` | Removido UUID contrapartida en List/Detail | §18 |
| `services/selectors.py` | UUID único en LIST_FIELDS/DETAIL_FIELDS | §4 |
| `offcanvas_crear_gasto.html` | Sección "Integración Contable" con gasto solamente | §18 |
| `offcanvas_editar_gasto.html` | Sección "Integración Contable" con gasto solamente | §18 |
| `gasto_editor.js` | `collectData()` captura UUID gasto únicamente | §18 |

---

## 📚 Referencias

- **Arquitectura base:** `AGENTS.md` § 2, 4, 13, 14, 18, 22, 23
- **Patrón coherente:** Todas las 6 apps (clientes, facturas, inventario, empleados, proveedores, gastos)
- **Orquestación contable:** `apps/tenant/contabilidad/integracion/extractores/` (futuro)

---

**Última Actualización:** 2026-05-13  
**Status:** ✅ **GASTOS INTEGRADO — §18 CUMPLIDO — CONTRAPARTIDA ORQUESTADA POR CONTABILIDAD**
