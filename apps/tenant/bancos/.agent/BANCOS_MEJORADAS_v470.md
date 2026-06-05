# Mejoras Módulo Bancos — v4.7.0

**Fecha:** 2026-06-04  
**Estado:** ✅ IMPLEMENTADO  
**Versión:** v4.7.0

---

## Resumen Ejecutivo

Se refactorizó el módulo **Bancos** (`apps/tenant/bancos/`) para mejorar la presentación de transacciones y conectar conciliación bancaria con **Facturas** y **Proveedores** via soft references (UUID). 

**Cambios principales:**
1. ✅ **Presentación visual mejorada**: valores con +/− signos (ingresos/egresos)
2. ✅ **Filtros por tipo de movimiento**: DEBITO (egreso) / CREDITO (ingreso)
3. ✅ **Conciliación mejorada**: vincular transacciones a facturas y proveedores
4. ✅ **Endpoints de búsqueda**: autocomplete para facturas y proveedores
5. ✅ **Tabla interactiva**: nueva JS con Tabulator para gestión visual

---

## Cambios Implementados

### 1. Backend — Serializers (`api/serializers.py`)

**TransaccionBancariaListSerializer — Nuevos campos:**

```python
factura_info        = SerializerMethodField()  # read-only snapshot de factura
proveedor_info      = SerializerMethodField()  # read-only snapshot de proveedor
conciliacion_display = SerializerMethodField()  # display legible de estado
```

**Lógica:**
- Si `factura_uuid` y `proveedor_uuid` están presentes → muestra "Vinculado a Factura y Proveedor"
- Si solo `factura_uuid` → "Vinculado a Factura"
- Si solo `proveedor_uuid` → "Vinculado a Proveedor"
- Si `conciliado=True` sin refs → "Conciliado"
- Si `conciliado=False` → "No conciliado"

---

### 2. Backend — ViewSet (`api/viewsets.py`)

**TransaccionBancariaViewSet — Mejoras:**

#### A) Filtro por extracto_uuid (query param)
```python
# GET /api/v1/bancos/transacciones/?extracto_uuid=<uuid>
extracto_uuid = self.request.query_params.get('extracto_uuid')
if extracto_uuid:
    qs = qs.filter(extracto__uuid=extracto_uuid)
```

#### B) Filtros Django por tipo_movimiento y conciliado
```python
filterset_fields = ["tipo_movimiento", "conciliado"]
# GET /api/v1/bancos/transacciones/?tipo_movimiento=DEBITO&conciliado=true
```

#### C) Endpoint: Buscar Facturas (autocomplete)
```
GET /api/v1/bancos/transacciones/search-facturas/?q=<numero_o_cliente>&page_size=10
Retorna: { results: [{ uuid, numero, receptor, total, fecha }] }
```

#### D) Endpoint: Buscar Proveedores (autocomplete)
```
GET /api/v1/bancos/transacciones/search-proveedores/?q=<nit_o_nombre>&page_size=10
Retorna: { results: [{ uuid, numero_documento, razon_social }] }
```

#### E) Endpoint: Conciliar Transacción (ya existía, se preservó)
```
PATCH /api/v1/bancos/transacciones/{uuid}/conciliar/
Body: { factura_uuid, proveedor_uuid, conciliado }
```

---

### 3. Frontend — Nueva tabla de transacciones (`static/bancos/js/features/transaccion_list.js`)

**Archivo nuevo con:**

| Característica | Descripción |
|---|---|
| **Columnas** | Fecha, Descripción, Tipo Movimiento, Valor (±), Saldo, Conciliación, Acciones |
| **Formatos** | Valor: `+$500,000` (ingreso) o `−$85,000` (egreso) |
| **Badges** | DEBITO (rojo, icono ↓), CREDITO (verde, icono ↑) |
| **Filtros** | Por tipo (`DEBITO`/`CREDITO`/Todos) y conciliación (Sí/No/Todos) |
| **Ordenamiento** | Fecha descending, valor, saldo, estado |
| **Acciones** | Botón "Conciliar" abre modal modal para vincular |

**Formatter de Valor:**
```javascript
function fmtValor(cell) {
  const val = parseFloat(cell.getValue()) || 0;
  const prefix = val >= 0 ? '+' : '';
  const cls = val >= 0 ? 'text-success' : 'text-danger';
  return `<span class="${cls} fw-semibold">${prefix}${COP(val)}</span>`;
}
```

**Colores por tipo:**
- **DEBITO**: `bg-danger` (rojo, egreso/descuento)
- **CREDITO**: `bg-success` (verde, ingreso)

---

### 4. Template Detalle Extracto (`templates/tenant/bancos/offcanvas_detalle_extracto.html`)

**Mejoras visuales:**
1. **Panel de Conciliación inline**: aparece al hacer click en una fila de transacción
2. **Campos UUID**: input para `factura_uuid` y `proveedor_uuid` (manual paste para MVP)
3. **Botones**:
   - ✅ "Guardar vínculo" → PATCH /conciliar/
   - ❌ "Quitar vínculo" → PATCH /conciliar/ con null values
   - "Cancelar" → oculta panel

**Lógica JavaScript inline:**
- Click en fila → carga UUIDs en panel de conciliación
- Guardar → PATCH con validación DSV en backend
- Actualización visual inmediata (badge pasa de "Pendiente" a "Factura"/etc.)

---

## Flujo End-to-End

### Caso 1: Vincular a Factura

1. Usuario abre **Detalle de Extracto**
2. Hace click en una transacción → panel de conciliación aparece
3. Campo "UUID Factura" queda vacío
4. Usuario abre otra pestaña y busca la factura o copia el UUID
5. Pega el UUID en el campo
6. Hace click "Guardar vínculo"
7. Backend:
   - Valida `factura_uuid` existencia via DSV
   - Verifica que pertenece a `empresa_id`
   - Marca `conciliado=True`
   - Retorna transacción actualizada
8. Frontend: badge cambia a "Factura" (verde)

### Caso 2: Vincular a Proveedor + Desvincu lar

1. Usuario abre panel, ingresa `proveedor_uuid`
2. Hace "Guardar vínculo"
3. Verifica que era proveedor → badge "Proveedor"
4. Después: hace click "Quitar vínculo"
5. Backend: `conciliado=false`, UUIDs = null
6. Frontend: badge vuelve a "Pendiente" (gris)

---

## Campos de Modelo (Sin Cambios)

```python
class TransaccionBancaria(SintelTenantBaseModel):
    # ... campos existentes ...
    factura_uuid    = UUIDField(null=True, blank=True, db_index=True)
    proveedor_uuid  = UUIDField(null=True, blank=True, db_index=True)
    conciliado      = BooleanField(default=False)
    
    @property
    def tipo_movimiento(self):
        """'DEBITO' si valor < 0, 'CREDITO' si valor >= 0"""
        return 'DEBITO' if self.valor < Decimal('0') else 'CREDITO'
```

---

## API Endpoints (Resumen)

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/v1/bancos/transacciones/?extracto_uuid=<uuid>` | Lista transacciones de un extracto |
| GET | `/api/v1/bancos/transacciones/?tipo_movimiento=DEBITO` | Filtra por tipo |
| GET | `/api/v1/bancos/transacciones/?conciliado=true` | Filtra conciliadas |
| GET | `/api/v1/bancos/transacciones/search-facturas/?q=<term>` | Busca facturas (autocomplete) |
| GET | `/api/v1/bancos/transacciones/search-proveedores/?q=<term>` | Busca proveedores |
| PATCH | `/api/v1/bancos/transacciones/{uuid}/conciliar/` | Vincula a factura/proveedor |

---

## Testing Checklist

- [ ] GET `/api/v1/bancos/transacciones/` → retorna `tipo_movimiento`, `factura_info`, `proveedor_info`, `conciliacion_display`
- [ ] GET `/api/v1/bancos/transacciones/?tipo_movimiento=DEBITO` → solo egresos
- [ ] GET `/api/v1/bancos/transacciones/?tipo_movimiento=CREDITO` → solo ingresos
- [ ] GET `/api/v1/bancos/transacciones/?conciliado=true` → solo conciliadas
- [ ] GET `/api/v1/bancos/transacciones/search-facturas/?q=100` → devuelve facturas
- [ ] GET `/api/v1/bancos/transacciones/search-proveedores/?q=abc` → devuelve proveedores
- [ ] PATCH `/api/v1/bancos/transacciones/{uuid}/conciliar/` con `factura_uuid` → OK 201 y marca `conciliado=true`
- [ ] Tabla de transacciones: valores con +/− visibles correctamente
- [ ] Badges DEBITO (rojo) y CREDITO (verde) se muestran
- [ ] Panel de conciliación aparece al click y desaparece al cancelar
- [ ] Actualización visual en badge tras guardar

---

## Próximas Fases (Roadmap)

1. **Fase 2 (v4.8.0)**: Autocomplete visual en panel de conciliación (búsqueda real vs. paste UUID)
2. **Fase 3 (v4.9.0)**: Sincronización automática de DIAN con transacciones bancarias
3. **Fase 4 (v5.0.0)**: Dashboard de conciliación con KPIs (% reconciliado, monto pendiente, etc.)

---

## Notas Técnicas

- **Zero-Trust DSV**: Backend valida `empresa_id` en todos los endpoints
- **Soft References**: `factura_uuid` y `proveedor_uuid` son referencias débiles, no ForeignKeys (Bounded Context §18)
- **Compatibilidad**: Migrations no requeridas (campos ya existían en modelo)
- **Formato Valor**: Negativo = DEBITO (−$), Positivo = CREDITO (+$) per `@property tipo_movimiento`
