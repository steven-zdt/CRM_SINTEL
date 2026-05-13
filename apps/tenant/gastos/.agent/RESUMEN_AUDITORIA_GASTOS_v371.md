# Resumen Auditoría: Gastos-Contabilidad v3.7.1

**Fecha:** 2026-05-13  
**Status:** ✅ **IMPLEMENTADO — CONTRAPARTIDA ORQUESTADA**

---

## 🎯 Cambio Arquitectónico

**Antes:** Apps decidían contrapartida (`cuenta_contrapartida_uuid`)  
**Ahora:** Contabilidad orquesta contrapartida (determina según reglas)

---

## 📋 Lo Que Se Implementó

### ✅ Campo Único en Modelo

**Archivo:** `apps/tenant/gastos/models.py`

```python
# SOLO cuenta de gasto — contrapartida responsabilidad contabilidad
cuenta_gasto_uuid = models.UUIDField(
    null=True, blank=True, db_index=True,
    help_text="UUID de CuentaContable de resultado. Contabilidad determina contrapartida."
)
```

**Removido:** `cuenta_contrapartida_uuid` (migración 0014)

---

### ✅ Migración Nueva

**Archivo:** `migrations/0014_remove_cuenta_contrapartida_uuid.py`

```python
operations = [
    migrations.RemoveField(
        model_name='documentosoporte',
        name='cuenta_contrapartida_uuid',
    ),
]
```

---

### ✅ Serializers Actualizados

**Archivo:** `apps/tenant/gastos/api/serializers.py`

#### DocumentoSoporteListSerializer
```python
cuenta_gasto_uuid = serializers.UUIDField(allow_null=True, read_only=True)
fields = (..., 'cuenta_gasto_uuid')
# Removido: cuenta_contrapartida_uuid
```

#### DocumentoSoporteDetailSerializer
```python
cuenta_gasto_uuid = serializers.UUIDField(allow_null=True, required=False)
fields = (..., 'cuenta_gasto_uuid')
# Removido: cuenta_contrapartida_uuid
```

---

### ✅ Templates Actualizados

#### `offcanvas_crear_gasto.html`
Sección "Integración Contable" con SOLO cuenta de gasto:
```html
<h6 class="text-success">Integración Contable</h6>
<input type="hidden" id="cuenta_gasto_uuid" name="cuenta_gasto_uuid">
<input type="text" id="cuenta_gasto_display" readonly>
<small>Contabilidad determinará la contrapartida automáticamente</small>
```

#### `offcanvas_editar_gasto.html`
Mismo patrón que crear.

---

### ✅ JavaScript Actualizado

**Archivo:** `gasto_editor.js`

#### `collectData()` (v3.7.1)
```javascript
function collectData(form) {
    const gastoUuidVal = form.querySelector('#cuenta_gasto_uuid')?.value;

    return {
        documento_soporte: {
            // ... campos existentes ...
            cuenta_gasto_uuid: gastoUuidVal || null
            // NO envía contrapartida (contabilidad la determina)
        }
    };
}
```

---

### ✅ Selectors Actualizados

**Archivo:** `services/selectors.py`

```python
DOCUMENTO_LIST_FIELDS = (
    ..., 'cuenta_gasto_uuid'  # Removido: cuenta_contrapartida_uuid
)

DOCUMENTO_DETAIL_FIELDS = (
    ..., 'cuenta_gasto_uuid'  # Removido: cuenta_contrapartida_uuid
)
```

---

## 🔍 Verificación §18

| Regla | Estado | Detalle |
|-------|--------|---------|
| **§2 Bounded Contexts** | ✅ PASS | Gastos NO importa contabilidad |
| **§18 Pull Model** | ✅ PASS | UUID opaco único de gasto |
| **Orquestación** | ✅ PASS | Contrapartida = responsabilidad contabilidad |
| **§13 DSV/IDOR** | ✅ PASS | empresa_id filtering en selectors |
| **§14 UUID Snapshot** | ✅ PASS | UUIDField opaco, sin FK |
| **§4 Zero Waste** | ✅ PASS | Campos en LIST_FIELDS/DETAIL_FIELDS |

---

## 🎯 Patrón Consistente — 6 Apps

| App | Campo Principal | Contrapartida | Status |
|-----|-----------------|---------------|--------|
| Clientes | ✅ 1x UUID | Contabilidad | ✅ |
| Facturas | ✅ 1x UUID | Contabilidad | ✅ |
| Inventario | ✅ 3x UUID | Contabilidad | ✅ |
| Empleados | ✅ 1x UUID | Contabilidad | ✅ |
| Proveedores | ✅ 1x UUID | Contabilidad | ✅ |
| **Gastos** | ✅ 1x UUID | Contabilidad | **✅** |

**Arquitectura:** Todas las apps proporcionan datos UUID, **contabilidad orquesta contrapartidas**.

---

## 📊 Cambios Resumidos

| Componente | Cambio | Status |
|-----------|--------|--------|
| **Modelo** | Removido campo contrapartida | ✅ |
| **Migración** | 0014_remove_cuenta_contrapartida_uuid | ✅ |
| **Serializers** | UUID único en List + Detail | ✅ |
| **Templates** | Sección gasto solamente | ✅ |
| **JavaScript** | collectData() solo captura gasto | ✅ |
| **Selectors** | UUID único en fields tuples | ✅ |

---

## 🏗️ Decisión Arquitectónica

**Por qué contrapartida en contabilidad:**
- Gastos es un módulo de negocio (registra egresos)
- Contabilidad es un módulo de orquestación (determina cómo contabilizar)
- Reglas de contrapartida dependen de contexto contable, no de datos de negocio
- Escalable: cambios a reglas = cambios en contabilidad, no en 6 apps

---

## 📚 Documentación Generada

**Auditoría Completa:**
`apps/tenant/gastos/.agent/AUDITORIA_INTEGRACION_GASTOS_CONTABILIDAD.md`

Incluye:
- Análisis detallado de cada componente
- Decisiones arquitectónicas (orquestación)
- Patrón coherente con 6 apps
- Referencias a AGENTS.md

---

## ⏳ Próximos Pasos

1. **ExtractorGastos** (en contabilidad)
   - Lee DocumentoSoporte.cuenta_gasto_uuid
   - Aplica reglas contables
   - Determina contrapartida
   - Genera asientos automáticos

2. **Orquestador de Contrapartidas** (en contabilidad)
   - Mapea tipo transacción → regla contrapartida
   - Ejemplo: Gasto → Bancos o CxP según política

---

**✅ IMPLEMENTACIÓN COMPLETADA — §18 CUMPLIDO — CONTRAPARTIDA ORQUESTADA**

Fecha: 2026-05-13  
Versión: v3.7.1
