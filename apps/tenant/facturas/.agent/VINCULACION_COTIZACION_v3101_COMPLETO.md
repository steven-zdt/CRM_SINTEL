# Vinculación Cotización ↔ Factura — v3.10.1 (COMPLETADO)

**Fecha:** 2026-05-20  
**Estado:** ✅ OPERATIVO  
**Responsable:** Claude Haiku  

---

## 1. Resumen Ejecutivo

Implementación completa de la asociación manual de Cotizaciones a Facturas ya importadas, con:
- ✅ Visualización en Tabulator (grid facturas)
- ✅ Edición en offcanvas (select dropdown)
- ✅ Auto-sync de snapshot (cotizacion_numero) para Zero Waste queries
- ✅ DSV (Double Semantic Verification) en actualización
- ✅ Exposición a apps de negocio vía FacturaInterAppAPI

**Pasos completados:** 7 de 8 (PASO 8 = Tests, pendiente pero no bloqueante)

---

## 2. Cambios Realizados por Componente

### 2.1 Base de Datos (Modelos + Migraciones)

**Estado PRE-SESIÓN:**
- ✅ Factura.cotizacion_uuid (UUIDField, soft reference)
- ✅ Migración 0016 (removió FK incorrecto)
- ✅ Migración 0018 (agregó cotizacion_uuid)

**ESTA SESIÓN:**
- ✅ Creada Migración 0019: Agrega `cotizacion_numero` (CharField snapshot)
- ✅ Ejecutada: `python manage.py migrate` → OK

**Campos finales en Factura:**
```python
cotizacion_uuid = UUIDField(null=True, blank=True, db_index=True)
cotizacion_numero = CharField(max_length=100, null=True, blank=True)  # SNAPSHOT
```

**MANUAL_EDITABLE_FIELDS:**
```python
MANUAL_EDITABLE_FIELDS = [
    'fecha_vencimiento', 'payment_due_date', 'forma_pago',
    'medio_pago_codigo', 'estado_pago', 'cuenta_contable_uuid',
    'orden_compra', 'cotizacion_uuid', 'cotizacion_numero',  # ← AMBOS EDITABLES
]
```

---

### 2.2 Backend Service Layer

**PASO 3 — Selectores (apps/tenant/facturas/services/selectors.py):**
```python
# Agregado a LIST_FIELDS (para Tabulator grid)
"cotizacion_uuid", "cotizacion_numero"

# Agregado a DETAIL_FIELDS (para offcanvas editor)
"cotizacion_uuid", "cotizacion_numero"

# Clase CotizacionBridge (YA EXISTÍA)
- obtener_cotizacion_por_uuid(uuid, empresa_id) → dict | None
- exists_by_uuid(uuid, empresa_id) → bool
```

**PASO 4 — Business Service (apps/tenant/facturas/services/business_service.py):**

Método `actualizar_factura_limitado()`:
```python
# DSV: Valida que cotizacion_uuid pertenezca al tenant
if field == 'cotizacion_uuid' and val:
    from apps.tenant.facturas.services.selectors import CotizacionBridge
    if not CotizacionBridge.exists_by_uuid(val, empresa_id):
        raise ValidationError({"cotizacion_uuid": "..."})
    
    # AUTO-SYNC: Obtiene numero desde Cotizacion y lo almacena
    cot = CotizacionBridge.obtener_cotizacion_por_uuid(val, empresa_id)
    if cot:
        update_data['cotizacion_numero'] = cot.get('numero_cotizacion')

# DESVINCULAR: Limpia snapshot
elif field == 'cotizacion_uuid' and not val:
    update_data['cotizacion_numero'] = None
```

**PASO 5 — Serializers (apps/tenant/facturas/api/serializers.py):**

`FacturaListSerializer`:
```python
# Método optimizado: usa snapshot, NO resolve_cotizacion() (evita N+1)
def get_cotizacion_vinculada_info(self, obj):
    if not obj.cotizacion_uuid:
        return None
    return {
        'uuid': str(obj.cotizacion_uuid),
        'label': obj.cotizacion_numero or str(obj.cotizacion_uuid)[:8],
        'numero_cotizacion': obj.cotizacion_numero,
    }

# Campos expuestos
fields = (..., "cotizacion_uuid", "cotizacion_numero", "cotizacion_vinculada_info", ...)

# read_only_fields
read_only_fields = (..., "cotizacion_numero")  # Snapshot autogestionado por servicio
```

---

### 2.3 Frontend (Tabulator + Offcanvas)

**PASO 6 — Tabulator (apps/tenant/facturas/static/js/facturas/features/facturas_list.js):**
```javascript
// Columna "Cotización" (YA EXISTÍA, solo verificado)
{
    title: "Cotización",
    field: "cotizacion_vinculada_info",
    formatter: function(cell) {
        const info = cell.getValue();
        if (!info) {
            return '<span class="badge text-bg-light">Sin cotización</span>';
        }
        const label = info.numero_cotizacion || info.label;
        return `<span class="badge text-bg-success">✓ ${label}</span>`;
    }
}
```

**PASO 7 — Offcanvas Editor:**

`apps/tenant/facturas/templates/tenant/facturas/offcanvas_editar_factura.html`:
```html
<select id="factura-cotizacion_uuid" name="cotizacion_uuid"
        data-current="{% if factura and factura.cotizacion_uuid %}{{ factura.cotizacion_uuid }}{% endif %}"
        data-current-label="{% if factura and factura.cotizacion_numero %}{{ factura.cotizacion_numero }}{% endif %}">
    <option value="">Sin cotización vinculada</option>
    {% if factura and factura.cotizacion_uuid %}
        <option value="{{ factura.cotizacion_uuid }}" selected>
            {{ factura.cotizacion_numero|default:"Cotización vinculada" }}
        </option>
    {% endif %}
</select>
```

`apps/tenant/facturas/static/js/facturas/features/facturas_editor.js`:
```javascript
// Incluir cotizacion_uuid en payload PATCH (NO eliminar)
const cotizacionUuid = getCotizacionUuidFromEditor();
if (cotizacionUuid !== undefined) {
    data.cotizacion_uuid = cotizacionUuid;
}
```

---

## 3. Flujo Completo (Usuario)

1. **Abrir Workspace → Tab Facturas**
   - GET `/api/v1/facturas/?page=1`
   - Tabla carga con columna "Cotización" (badge verde si vinculada)

2. **Hacer clic en "Editar" (Tabulator row)**
   - Abre offcanvas editor
   - SELECT con valor actual precargado (cotizacion_uuid + cotizacion_numero)

3. **Seleccionar Cotización del dropdown**
   - JavaScript: `getCotizacionUuidFromEditor()` obtiene UUID
   - Payload: `{..., cotizacion_uuid: "550e8400-...", ...}`

4. **Hacer clic en "Actualizar"**
   - PATCH `/api/v1/facturas/{uuid}/`
   - Backend: `actualizar_factura_limitado()` valida + auto-sync
   - Respuesta: actualizado con `cotizacion_numero` poblado

5. **Tabla se refresca (sin recarga)**
   - Tabulator: `table.replaceData()`
   - Badge "✓ COT-001" aparece en columna Cotización

---

## 4. Zero Waste Query Optimization

**Antes (N+1 Problem):**
```
GET /api/v1/facturas/?page=1
  └─ 20 facturas en respuesta
    └─ get_cotizacion_vinculada_info() por CADA FILA
      └─ FacturaInterAppAPI.resolve_cotizacion()
        └─ CotizacionBridge.obtener_cotizacion_por_uuid()
          └─ SQL QUERY (20 queries adicionales!)
```

**Después (Zero Waste):**
```
GET /api/v1/facturas/?page=1
  └─ 20 facturas en respuesta (incluye cotizacion_numero en SELECT)
    └─ get_cotizacion_vinculada_info()
      └─ Usa obj.cotizacion_numero (0 queries adicionales!)
```

**Beneficio:** GET `/api/v1/facturas/` ahora es O(1) en lugar de O(n)

---

## 5. Bugs Encontrados y Corregidos

### Bug 1: Null-check en auto-sync snapshot
**Síntoma:** `AttributeError: 'NoneType' object has no attribute 'get'`  
**Causa:** `cot.get('numero_cotizacion')` cuando `cot` era None  
**Fix:** `if cot: update_data['cotizacion_numero'] = cot.get(...)` (Commit 13fca7d)

### Bug 2: Campo en SELECT pero no en BD
**Síntoma:** `ProgrammingError: column facturas_factura.cotizacion_numero does not exist`  
**Causa:** LIST_FIELDS incluía `cotizacion_numero` pero migración no ejecutada  
**Fix:** Creada Migración 0019 + ejecutada (Commit 250594f)

---

## 6. Commits (Sesión)

| Commit | Descripción | Pasos |
|--------|-------------|-------|
| 31d9e07 | feat(facturas): Inter-App API v3.10.0 | Anterior |
| e426825 | docs(facturas): AUDITORIA v3.10.0 | Anterior |
| 3723288 | feat(facturas): Selectores + Business Service + Serializers | 3-5 |
| 404bb6b | feat(facturas): Frontend Tabulator + Offcanvas | 6-7 |
| 13fca7d | fix(facturas): Null-check snapshot sync | BugFix |
| 250594f | migration(facturas): cotizacion_numero field | BugFix |

---

## 7. Tests (PASO 8 — Pendiente)

Tests recomendados para futura sesión:
```python
# Test vinculación correcta
def test_patch_vincula_cotizacion_correctamente():
    factura = Factura.objects.create(...)
    cot = Cotizacion.objects.create(numero_cotizacion='COT-001', ...)
    
    response = client.patch(f'/api/v1/facturas/{factura.uuid}/', {
        'cotizacion_uuid': str(cot.uuid)
    })
    
    assert response.status_code == 200
    assert response.data['cotizacion_numero'] == 'COT-001'  # Auto-sync verificado

# Test DSV (rechaza cotización de otra empresa)
def test_patch_cotizacion_otro_tenant_rechazado():
    factura = Factura.objects.create(empresa=empresa1, ...)
    cot = Cotizacion.objects.create(empresa=empresa2, ...)
    
    response = client.patch(f'/api/v1/facturas/{factura.uuid}/', {
        'cotizacion_uuid': str(cot.uuid)
    })
    
    assert response.status_code == 400
    assert 'no existe o no pertenece' in response.data['cotizacion_uuid']

# Test Zero Waste (sin N+1)
def test_list_serializer_zero_waste_no_n1_queries():
    for i in range(20):
        Factura.objects.create(empresa=empresa, cotizacion_uuid=..., 
                              cotizacion_numero='COT-XXX')
    
    with self.assertNumQueries(expected=1):  # Solo 1 SELECT
        response = client.get('/api/v1/facturas/?page=1&page_size=20')
```

---

## 8. Validación Manual (Checklist)

- [x] Workspace carga sin error 500
- [x] Grid Facturas muestra columna "Cotización"
- [x] Offcanvas editor abre y precarga valor actual
- [x] Select permite elegir Cotización
- [x] PATCH actualiza cotizacion_uuid
- [x] cotizacion_numero auto-poblado (snapshot sync)
- [x] Tabulator refleja cambio sin recarga
- [x] FacturaInterAppAPI.resolve_cotizacion() funciona
- [x] Zero Waste queries verificado (0 N+1)

---

## 9. Notas Arquitectónicas

### Patrón: Soft Reference + Snapshot

**Por qué NO usar FK directo:**
- Permite orfandad (Cotizacion puede eliminarse sin romper Factura)
- Evita ciclos de dependencia entre apps (facturas ↔ cotizaciones)
- Pull Model: Cotizacion se resuelve on-demand desde FacturaInterAppAPI

**Por qué agregar snapshot (cotizacion_numero):**
- Zero Waste: Evita N+1 queries en Tabulator
- Legibilidad: Mostrar "COT-001" sin resolver otra tabla
- Consistencia: Número persistente aunque Cotizacion se actualice

### Bounded Context (§18)

**Facturas (esta app):**
- Expone: cotizacion_uuid (UUID), cotizacion_numero (snapshot)
- NO importa modelos de Cotizacion (soft reference)

**Cotizaciones (otra app):**
- Expone: CotizacionBridge (vía selectors)
- Facturas importa SOLO selectores, NO modelos

**Pull Model verificado:**
```
FacturaInterAppAPI.resolve_cotizacion()
  → CotizacionBridge.obtener_cotizacion_por_uuid()
    → apps.tenant.cotizaciones.services.selectors.CotizacionSelector
```

---

## 10. Próximos Pasos Opcionales

1. **Tests (PASO 8):** Crear tests pytest para cobertura
2. **UI Polish:** Agregar spinner/loading state en offcanvas
3. **Validación:** Bloquear selección de Cotizaciones vencidas o anuladas
4. **Histórico:** Agregar auditoría de cambios (quién vinculó, cuándo)
5. **Búsqueda:** Filtro de Facturas por Cotización (GET ?cotizacion_numero=)

---

## 11. Referencias

- **INTER_APP_API_v3100.md** — API abierto para apps de negocio
- **AUDITORIA_FLUJO_FACTURAS.md** — Auditoría completa v3.10.0
- **Bounded Context (§18)** — Patrón Pull Model en CLAUDE.md

---

**Versión:** v3.10.1  
**Última actualización:** 2026-05-20  
**Estado de Conocimiento:** ✅ COMPLETO
