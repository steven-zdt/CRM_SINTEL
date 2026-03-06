# Alineación en Cascada - Proyectos v3.3

## 📋 Flujo de Alineación

```
models.py (SSoT)
    ↓
services.py (Lógica de Negocio)
    ↓
serializers.py (Transformación API)
    ↓
viewsets.py (Endpoints REST)
    ↓
proyectos.api.js (Cliente HTTP)
    ↓
proyectos.page.js (UI Tabulator)
    ↓
proyectos.modals.js (Formularios)
```

---

## ✅ Checklist de Alineación

### 1. Modelo → Services
- [x] `calcular_costo_mano_obra()` usa `AsignacionPersonal`
- [x] `calcular_costo_materiales()` usa `ItemPedido`
- [x] `calcular_indicadores_financieros()` actualiza campos del modelo
- [x] `asignar_snapshot_cliente()` maneja `cliente_id` y `cliente_nombre`
- [x] `asignar_snapshot_responsable()` maneja responsables por fase
- [x] `cambiar_fase_proyecto()` valida fases y actualiza responsable
- [x] `crear_proyecto()` y `actualizar_proyecto()` usan snapshots

### 2. Services → Serializers
- [x] `ProyectoListSerializer` incluye campos calculados (`costo_total`, `utilidad_estimada`, `margen_rentabilidad`)
- [x] `ProyectoDetailSerializer` incluye `indicadores_financieros` (método)
- [x] Serializers manejan snapshots (`cliente_nombre`, `responsable_actual_nombre`)
- [x] `fecha_fin_prevista` es alias de `fecha_fin_estimada` (para compatibilidad frontend)

### 3. Serializers → ViewSets
- [x] `ProyectoViewSet` usa `ProyectoListSerializer` para `list()`
- [x] `ProyectoViewSet` usa `ProyectoDetailSerializer` para resto de acciones
- [x] `create()` y `update()` delegan a `services.py`
- [x] `partial_update()` también delega a `services.py`

### 4. ViewSets → proyectos.api.js
- [x] `list()` → `proyectosAPI.list()`
- [x] `retrieve()` → `proyectosAPI.get(id)`
- [x] `create()` → `proyectosAPI.create(data)`
- [x] `update()` → `proyectosAPI.update(id, data)`
- [x] `partial_update()` → `proyectosAPI.syncCostos(id)` (usa PATCH)
- [x] `destroy()` → `proyectosAPI.delete(id)`
- [x] ✅ `avanzarFase(id, fase)` - Implementado en backend (POST /api/v1/proyectos/{id}/avanzar-fase/)

### 5. proyectos.api.js → proyectos.page.js
- [x] `proyectos.page.js` usa `proyectosAPI.list()` para cargar datos
- [x] Columnas de Tabulator alineadas con `ProyectoListSerializer`
- [x] `formatCurrency()` usa `proyectosAPI.formatCurrency()`
- [x] Botones de acción usan `proyectosAPI.syncCostos()` y `proyectosAPI.delete()`

### 6. proyectos.api.js → proyectos.modals.js
- [x] `proyectos.modals.js` usa `proyectosAPI.get(id)` para editar
- [x] `proyectos.modals.js` usa `proyectosAPI.create()` y `proyectosAPI.update()`
- [x] Campos del formulario mapean correctamente con el modelo

---

## 🔍 Campos Críticos - Verificación

### Campos del Modelo (models.py)
```python
- codigo, nombre, tipo_servicio, descripcion
- cliente_id, cliente_nombre (snapshot)
- responsable_actual_id, responsable_actual_nombre (snapshot)
- fase_actual, estado_tarea
- fecha_inicio, fecha_fin_estimada
- valor_contrato_proyectado
- costo_mano_obra_real, costo_materiales_real (calculados)
- utilidad_estimada, margen_rentabilidad (calculados)
- porcentaje_avance, fecha_cierre_real
```

### Campos del Serializer (serializers.py)
```python
ProyectoListSerializer:
- id, codigo, nombre, tipo_servicio_display
- fase_actual, fase_actual_display
- estado_tarea, estado_display
- cliente_nombre, responsable_actual_nombre
- fecha_inicio, fecha_fin_estimada, fecha_fin_prevista (alias)
- valor_contrato_proyectado
- costo_total (calculado), utilidad_estimada, margen_rentabilidad
- porcentaje_avance, fecha_cierre_real
```

### Campos del Frontend (proyectos.page.js)
```javascript
getColumns():
- codigo, nombre, tipo_servicio_display
- fase_actual_display (con badges)
- estado_display (con badges)
- cliente_nombre, responsable_actual_nombre
- valor_contrato_proyectado, costo_total, utilidad_estimada
- porcentaje_avance (con progress bar)
```

### Campos del Formulario (proyectos.modals.js)
```javascript
save():
- codigo, nombre, tipo_servicio
- fase_actual, estado_tarea
- cliente_id, cliente_nombre
- responsable_actual_id, responsable_actual_nombre
- valor_contrato_proyectado
- fecha_inicio, fecha_fin_estimada
- descripcion
```

---

## ⚠️ Inconsistencias Detectadas

### 1. Método `avanzarFase` ✅ IMPLEMENTADO
- **Backend**: Endpoint `POST /api/v1/proyectos/{id}/avanzar-fase/` implementado en `viewsets.py`
- **Frontend**: `proyectos.api.js` tiene método `avanzarFase(id, fase, responsableId, responsableNombre)`
- **Estado**: ✅ Completado - Usa `cambiar_fase_proyecto()` del service layer

### 2. Alias `fecha_fin_prevista`
- **Modelo**: Solo tiene `fecha_fin_estimada`
- **Serializer**: Tiene `fecha_fin_prevista` como alias (read_only)
- **Frontend**: Usa `fecha_fin_prevista` en algunos lugares
- **Estado**: ✅ Correcto - El alias funciona correctamente

---

## ✅ Estado Final

1. ✅ **`avanzarFase` implementado** - Endpoint POST `/api/v1/proyectos/{id}/avanzar-fase/`
2. ✅ **Mapeo de campos verificado** - Todos los campos del formulario están correctamente mapeados
3. ✅ **Campos calculados** - Se actualizan automáticamente mediante `calcular_indicadores_financieros()`

---

## 📊 Resumen de Endpoints

| Método | Endpoint | ViewSet | API JS | Descripción |
|--------|----------|---------|--------|-------------|
| GET | `/api/v1/proyectos/` | `list()` | `list()` | Lista paginada |
| GET | `/api/v1/proyectos/{id}/` | `retrieve()` | `get(id)` | Detalle completo |
| POST | `/api/v1/proyectos/` | `create()` | `create(data)` | Crear proyecto |
| PUT | `/api/v1/proyectos/{id}/` | `update()` | `update(id, data)` | Actualizar completo |
| PATCH | `/api/v1/proyectos/{id}/` | `partial_update()` | `syncCostos(id)` | Actualizar parcial |
| POST | `/api/v1/proyectos/{id}/avanzar-fase/` | `avanzar_fase()` | `avanzarFase(id, fase)` | Cambiar fase PMI |
| DELETE | `/api/v1/proyectos/{id}/` | `destroy()` | `delete(id)` | Eliminar proyecto |
