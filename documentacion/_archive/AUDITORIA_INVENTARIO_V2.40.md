# 🔍 Auditoría Estática del Módulo de Inventario v2.40

**Fecha:** 2024  
**Auditor:** Lead QA Engineer & Arquitecto Django  
**Módulo:** `apps.tenant.inventario`

---

## 📋 Resumen Ejecutivo

Se realizó una auditoría estática completa del módulo de Inventario después de la refactorización masiva que separó la lógica en Productos, Servicios, Activos y Movimientos. Se identificaron **3 errores críticos** y **2 advertencias** que requieren corrección antes de pasar a producción.

---

## ✅ 1. VALIDACIÓN DE RUTAS (Backend ↔ Frontend)

### Estado: **✅ COHERENTE** (con observaciones menores)

#### Backend (`apps/tenant/inventario/api/urls.py`):
```python
router.register(r'categorias', CategoriaItemViewSet, basename='inv-categorias')
router.register(r'productos', ProductoViewSet, basename='inv-productos')
router.register(r'servicios', ServicioViewSet, basename='inv-servicios')
router.register(r'activos', ActivoFijoViewSet, basename='inv-activos')
router.register(r'movimientos', MovimientoInventarioViewSet, basename='inv-movimientos')
router.register(r'historial-servicios', HistorialServicioViewSet, basename='inv-historial-servicios')
```

#### Frontend (`inventario.api.js`):
```javascript
API_BASE = '/api/v1/inventario'
productos: { list, create, retrieve, update, delete, dt, stock }
servicios: { list, create, retrieve, update, delete, dt }
activos: { list, create, retrieve, update, delete, dt }
movimientos: { list, create, retrieve }
categorias: { list }
```

**✅ Coincidencias:**
- Todos los endpoints base coinciden correctamente
- Acciones `@action(detail=False, methods=["post"], url_path="dt")` están correctamente mapeadas en el JS como `.dt()`
- Endpoint `stock` en ProductoViewSet está correctamente expuesto

**⚠️ Observaciones:**
- `movimientos.page.js` usa `serverSide: true` pero el ViewSet **NO tiene acción `dt`**. Actualmente usa `ajax: { url: '/api/v1/inventario/movimientos/' }` que funciona pero no es DataTables server-side real.
- **Recomendación:** Implementar `@action(detail=False, methods=["post"], url_path="dt")` en `MovimientoInventarioViewSet` o cambiar a client-side.

---

## ✅ 2. VALIDACIÓN DE MODELOS Y SERIALIZERS

### Estado: **❌ ERRORES CRÍTICOS ENCONTRADOS**

#### Error 1: Tipos de Movimiento Inconsistentes

**Ubicación:** `services.py` línea 73, 80

**Problema:**
```python
# services.py referencia tipos que NO existen en el modelo:
entradas = [
    MovimientoInventario.TipoMovimiento.ENTRADA_PROYECTO,  # ❌ NO EXISTE
]
salidas = [
    MovimientoInventario.TipoMovimiento.SALIDA_PROYECTO,  # ❌ NO EXISTE
    MovimientoInventario.TipoMovimiento.SALIDA_AJUSTE,     # ❌ NO EXISTE
]
```

**Modelo Real (`models.py` líneas 193-201):**
```python
class TipoMovimiento(models.TextChoices):
    # ENTRADAS
    ENTRADA_COMPRA = "ENTRADA_COMPRA", _("Compra")
    ENTRADA_AJUSTE = "ENTRADA_AJUSTE", _("Ajuste (+)")
    ENTRADA_DEVOLUCION = "ENTRADA_DEVOLUCION", _("Devolución Cliente")
    # SALIDAS
    SALIDA_VENTA = "SALIDA_VENTA", _("Venta")
    SALIDA_BAJA = "SALIDA_BAJA", _("Baja / Deterioro")
    SALIDA_CONSUMO = "SALIDA_CONSUMO", _("Consumo Interno")
```

**Corrección Requerida:**
```python
# services.py - Función recalcular_stock_producto()
entradas = [
    MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA,
    MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE,
    MovimientoInventario.TipoMovimiento.ENTRADA_DEVOLUCION,
]

salidas = [
    MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
    MovimientoInventario.TipoMovimiento.SALIDA_BAJA,
    MovimientoInventario.TipoMovimiento.SALIDA_CONSUMO,
]
```

#### Error 2: Service Layer No Conectado en ViewSet

**Ubicación:** `viewsets.py` línea 317-318

**Problema:**
```python
def perform_create(self, serializer):
    # ...
    serializer.save(empresa=empresa)
    
    # Nota: Aquí deberías llamar al Service Layer para actualizar el stock_actual del Producto
    # ej: actualizar_stock_producto(serializer.instance)
    # ❌ COMENTARIO NO IMPLEMENTADO - El stock NO se actualiza automáticamente
```

**Impacto:** Al crear un movimiento, el `stock_actual` del producto **NO se recalcula**, rompiendo la integridad del Kardex.

**Corrección Requerida:**
```python
def perform_create(self, serializer):
    from apps.tenant.inventario.services import recalcular_stock_producto
    
    empresa = Empresa.objects.first()
    movimiento = serializer.save(empresa=empresa)
    
    # ⚠️ CRÍTICO: Recalcular stock después de crear movimiento
    recalcular_stock_producto(movimiento.producto.id)
    
    return movimiento
```

#### ✅ Validación de Serializers

**Campos en Serializers que dependen de relaciones:**
- `ProductoSerializer.categoria_nombre` → `source='categoria.nombre'` ✅ Correcto
- `ServicioSerializer.categoria_nombre` → `source='categoria.nombre'` ✅ Correcto
- `ActivoFijoSerializer.categoria_nombre` → `source='categoria.nombre'` ✅ Correcto
- `ActivoFijoSerializer.estado_display` → `source='get_estado_display'` ✅ Correcto
- `MovimientoInventarioSerializer.producto_nombre` → `source='producto.nombre'` ✅ Correcto
- `MovimientoInventarioSerializer.tipo_display` → `source='get_tipo_display'` ✅ Correcto

**Optimización de Querysets:**
- `ProductoViewSet.queryset` → `select_related('categoria')` ✅ Correcto
- `ServicioViewSet.queryset` → `select_related('categoria')` ✅ Correcto
- `ActivoFijoViewSet.queryset` → `select_related('categoria', 'empresa')` ✅ Correcto
- `MovimientoInventarioViewSet.queryset` → `select_related('producto')` ✅ Correcto

**✅ No hay problemas de N+1 queries detectados.**

---

## ✅ 3. COHERENCIA UI (HTML ↔ JS)

### Estado: **✅ COHERENTE** (con 1 advertencia)

#### Validación de IDs Críticos:

| Componente | HTML ID | JS Selector | Estado |
|------------|---------|-------------|--------|
| **Productos** | | | |
| Tabla | `#table-inventario-productos` | `#table-inventario-productos` | ✅ |
| Form | `#form-producto` | `$('#form-producto')` | ✅ |
| Modal | `#modal-producto` | `$('#modal-producto')` | ✅ |
| Botón Crear | `#btn-nuevo-producto` | `$('#btn-nuevo-producto')` | ✅ |
| Botón Guardar | `#btn-guardar-producto` | `$('#btn-guardar-producto')` | ✅ |
| **Servicios** | | | |
| Tabla | `#table-inventario-servicios` | `#table-inventario-servicios` | ✅ |
| Form | `#form-servicio` | `$('#form-servicio')` | ✅ |
| Modal | `#modal-servicio` | `$('#modal-servicio')` | ✅ |
| Botón Crear | `#btn-nuevo-servicio` | `$('#btn-nuevo-servicio')` | ✅ |
| Botón Guardar | `#btn-guardar-servicio` | `$('#btn-guardar-servicio')` | ✅ |
| **Activos** | | | |
| Tabla | `#table-inventario-activos` | `#table-inventario-activos` | ✅ |
| Form | `#form-activo` | `$('#form-activo')` | ✅ |
| Modal | `#modal-activo` | `#modal-activo` | ✅ |
| Botón Crear | `#btn-nuevo-activo` | `$('#btn-nuevo-activo')` | ✅ |
| Botón Guardar | `#btn-guardar-activo` | `$('#btn-guardar-activo')` | ✅ |
| **Movimientos** | | | |
| Tabla | `#table-inventario-movimientos` | `#table-inventario-movimientos` | ✅ |
| Form | `#form-movimiento` | `$('#form-movimiento')` | ✅ |
| Modal | `#modal-movimiento` | `$('#modal-movimiento')` | ✅ |
| Botón Crear | `#btn-nuevo-movimiento` | `$('#btn-nuevo-movimiento')` | ✅ |
| Botón Guardar | `#btn-guardar-movimiento` | `$('#btn-guardar-movimiento')` | ✅ |

**⚠️ Advertencia:**
- `movimientos.page.js` usa `$('#modal-movimiento').modal('show')` (Bootstrap 4) pero el HTML puede estar usando Bootstrap 5. Verificar compatibilidad.

---

## 📊 4. VALIDACIÓN DE SERVICE LAYER

### Estado: **❌ ERROR CRÍTICO**

#### Problema: Service Layer No Invocado

**Ubicación:** `viewsets.py` - `MovimientoInventarioViewSet.perform_create()`

**Análisis:**
- ✅ La función `recalcular_stock_producto()` existe y está correctamente implementada
- ✅ La función `registrar_movimiento()` existe y llama automáticamente a `recalcular_stock_producto()`
- ❌ **PERO** el ViewSet **NO usa** estas funciones del service layer
- ❌ El ViewSet crea el movimiento directamente con `serializer.save()`, **sin actualizar el stock**

**Impacto:**
- Los movimientos se crean correctamente
- El `stock_actual` del producto **NO se actualiza**
- La tabla de productos muestra stock desactualizado
- **ROMPE LA INTEGRIDAD DEL KARDEX**

**Corrección Requerida:**
```python
# viewsets.py - MovimientoInventarioViewSet
def perform_create(self, serializer):
    from apps.tenant.empresa.models import Empresa
    from apps.tenant.inventario.services import registrar_movimiento
    
    empresa = Empresa.objects.first()
    if not empresa:
        raise ValueError("No se encontró configuración de Empresa para este tenant.")
    
    # ⚠️ CRÍTICO: Usar service layer en lugar de serializer.save() directo
    movimiento = registrar_movimiento(
        producto_id=serializer.validated_data['producto'].id,
        tipo=serializer.validated_data['tipo'],
        cantidad=serializer.validated_data['cantidad'],
        empresa=empresa,
        costo_unitario=serializer.validated_data.get('costo_unitario', 0),
        origen_referencia=serializer.validated_data.get('origen_referencia'),
        cliente_referencia=serializer.validated_data.get('cliente_referencia'),
        observaciones=serializer.validated_data.get('observaciones')
    )
    
    return movimiento
```

**Alternativa (si se quiere mantener el serializer):**
```python
def perform_create(self, serializer):
    from apps.tenant.empresa.models import Empresa
    from apps.tenant.inventario.services import recalcular_stock_producto
    
    empresa = Empresa.objects.first()
    movimiento = serializer.save(empresa=empresa)
    
    # ⚠️ CRÍTICO: Recalcular stock después de guardar
    recalcular_stock_producto(movimiento.producto.id)
    
    return movimiento
```

---

## 🧪 5. PLAN DE PRUEBAS DE HUMO (Happy Path)

### Pre-requisitos
- [ ] Corregir los 3 errores críticos identificados
- [ ] Aplicar migraciones: `python manage.py migrate_schemas --tenant`
- [ ] Acceder al workspace como usuario ADMIN
- [ ] Navegar a `#tab-inventario`

---

### **TEST 1: Flujo de Categoría**

**Objetivo:** Validar creación de categoría base

**Pasos:**
1. Ir a la pestaña "Categorías" (si existe) o crear categoría desde modal de Producto
2. Crear categoría:
   - **Nombre:** "General"
   - **Aplicación:** "Todos" (TODO)
   - **Activo:** ✅
3. Hacer clic en "Guardar"

**Resultado Esperado:**
- ✅ Categoría creada exitosamente
- ✅ Mensaje de éxito visible
- ✅ Categoría aparece en selector de Productos/Servicios

**Validación:**
```sql
-- Verificar en BD
SELECT * FROM tenant_inventario_categoriaitem WHERE nombre = 'General';
```

---

### **TEST 2: Flujo de Producto**

**Objetivo:** Validar creación de producto y visualización en tabla

**Pasos:**
1. Ir a pestaña "Productos"
2. Hacer clic en "Nuevo Producto" (`#btn-nuevo-producto`)
3. Llenar formulario:
   - **Código:** "CAM-IP-001"
   - **Nombre:** "Cámara IP"
   - **Categoría:** Seleccionar "General" (creada en TEST 1)
   - **Precio Venta:** 100000
   - **Stock Mínimo:** 5
   - **Activo:** ✅
4. Hacer clic en "Guardar Producto" (`#btn-guardar-producto`)

**Resultado Esperado:**
- ✅ Producto creado exitosamente
- ✅ Modal se cierra automáticamente
- ✅ Tabla DataTables se recarga (`dt.ajax.reload()`)
- ✅ Producto aparece en la tabla con:
  - Código: "CAM-IP-001"
  - Nombre: "Cámara IP"
  - Categoría: "General"
  - Stock: 0.00 (inicial)
  - Precio: $100,000 COP (formateado)

**Validación Backend:**
```sql
SELECT id, codigo, nombre, stock_actual, precio_venta 
FROM tenant_inventario_producto 
WHERE codigo = 'CAM-IP-001';
-- Debe retornar: stock_actual = 0, precio_venta = 100000
```

**Validación Frontend:**
- Abrir DevTools → Network
- Verificar llamada `POST /api/v1/inventario/productos/` → Status 201
- Verificar llamada `POST /api/v1/inventario/productos/dt/` después del guardado

---

### **TEST 3: Flujo de Kardex (Movimiento de Entrada)**

**Objetivo:** Validar registro de movimiento y actualización automática de stock

**Pasos:**
1. Ir a pestaña "Movimientos" (`#tab-inventario-movimientos`)
2. Hacer clic en "Nuevo Movimiento" (`#btn-nuevo-movimiento`)
3. Llenar formulario:
   - **Producto:** Seleccionar "CAM-IP-001 - Cámara IP (Stock: 0)"
   - **Tipo:** "Compra" (ENTRADA_COMPRA)
   - **Cantidad:** 10
   - **Costo Unitario:** 80000 (opcional)
   - **Referencia:** "Factura #12345"
   - **Observaciones:** "Compra inicial de stock"
4. Hacer clic en "Registrar Movimiento" (`#btn-guardar-movimiento`)

**Resultado Esperado:**
- ✅ Movimiento creado exitosamente
- ✅ Modal se cierra
- ✅ Tabla de Movimientos se recarga
- ✅ **CRÍTICO:** Tabla de Productos se recarga automáticamente (si está visible)
- ✅ En tabla de Productos, el stock de "Cámara IP" cambia de **0.00** a **10.00**

**Validación Backend:**
```sql
-- Verificar movimiento creado
SELECT id, tipo, cantidad, producto_id 
FROM tenant_inventario_movimientoinventario 
WHERE producto_id = (SELECT id FROM tenant_inventario_producto WHERE codigo = 'CAM-IP-001')
ORDER BY created_at DESC LIMIT 1;
-- Debe retornar: tipo = 'ENTRADA_COMPRA', cantidad = 10

-- Verificar stock actualizado
SELECT stock_actual 
FROM tenant_inventario_producto 
WHERE codigo = 'CAM-IP-001';
-- ⚠️ CRÍTICO: Debe retornar 10.00 (NO 0.00)
```

**Validación Frontend:**
- Abrir DevTools → Network
- Verificar llamada `POST /api/v1/inventario/movimientos/` → Status 201
- Verificar que después del guardado se ejecute:
  - `POST /api/v1/inventario/movimientos/dt/` (recarga tabla movimientos)
  - `POST /api/v1/inventario/productos/dt/` (recarga tabla productos - **CRÍTICO**)

**⚠️ SI EL STOCK NO SE ACTUALIZA:**
- El error crítico #2 (Service Layer no conectado) está presente
- Aplicar la corrección antes de continuar

---

### **TEST 4: Validación de Stock Actualizado**

**Objetivo:** Confirmar que el stock se actualizó correctamente después del movimiento

**Pasos:**
1. Volver a la pestaña "Productos"
2. Buscar "Cámara IP" en la tabla (o refrescar si no está visible)
3. Verificar columna "Stock"

**Resultado Esperado:**
- ✅ Stock muestra **10.00** (no 0.00)
- ✅ El valor está formateado correctamente (2 decimales)
- ✅ Si hay alerta de stock mínimo, debe mostrar que está por encima del mínimo (5)

**Validación Adicional:**
- Hacer clic en el botón "Editar" del producto
- Verificar que el campo `stock_actual` (si es visible) muestre 10.00
- **Nota:** `stock_actual` es `read_only` en el serializer, así que no debería ser editable

---

### **TEST 5: Movimiento de Salida (Opcional - Validación Completa)**

**Objetivo:** Validar que las salidas restan correctamente del stock

**Pasos:**
1. Ir a "Movimientos"
2. Crear nuevo movimiento:
   - **Producto:** "CAM-IP-001 - Cámara IP"
   - **Tipo:** "Venta" (SALIDA_VENTA)
   - **Cantidad:** 3
   - **Referencia:** "Venta #001"
3. Guardar

**Resultado Esperado:**
- ✅ Movimiento creado
- ✅ Stock de "Cámara IP" cambia de **10.00** a **7.00**

---

## 📝 RESUMEN DE ERRORES ENCONTRADOS

### ❌ **ERRORES CRÍTICOS (Bloquean Funcionalidad)**

1. **`services.py` - Tipos de Movimiento Inexistentes**
   - **Archivo:** `apps/tenant/inventario/services.py` líneas 73, 80
   - **Problema:** Referencia a `ENTRADA_PROYECTO`, `SALIDA_PROYECTO`, `SALIDA_AJUSTE` que no existen en el modelo
   - **Impacto:** La función `recalcular_stock_producto()` fallará con `AttributeError`
   - **Prioridad:** 🔴 **ALTA** - Bloquea cálculo de stock

2. **`viewsets.py` - Service Layer No Conectado**
   - **Archivo:** `apps/tenant/inventario/api/viewsets.py` línea 317
   - **Problema:** `MovimientoInventarioViewSet.perform_create()` no llama a `recalcular_stock_producto()`
   - **Impacto:** El stock NO se actualiza al crear movimientos, rompiendo la integridad del Kardex
   - **Prioridad:** 🔴 **ALTA** - Bloquea funcionalidad core

### ⚠️ **ADVERTENCIAS (No Bloquean pero Requieren Atención)**

3. **`movimientos.page.js` - DataTables Server-Side Incompleto**
   - **Archivo:** `apps/tenant/core/static/core/js/inventario/movimientos.page.js` línea 36
   - **Problema:** Usa `serverSide: true` pero el ViewSet no tiene acción `dt`
   - **Impacto:** Funciona pero no es DataTables server-side real (carga todos los registros)
   - **Prioridad:** 🟡 **MEDIA** - Puede causar problemas de rendimiento con muchos registros

4. **Bootstrap Version Mismatch (Potencial)**
   - **Archivo:** `movimientos.page.js` línea 66
   - **Problema:** Usa `.modal('show')` (Bootstrap 4) pero el proyecto puede usar Bootstrap 5
   - **Impacto:** Puede no funcionar si se migró a Bootstrap 5
   - **Prioridad:** 🟡 **MEDIA** - Verificar versión de Bootstrap en uso

---

## ✅ CHECKLIST DE CORRECCIÓN

### Antes de Ejecutar Pruebas de Humo:

- [ ] **Corregir Error #1:** Actualizar `services.py` para usar solo tipos de movimiento válidos
- [ ] **Corregir Error #2:** Conectar service layer en `MovimientoInventarioViewSet.perform_create()`
- [ ] **Opcional - Advertencia #3:** Implementar acción `dt` en `MovimientoInventarioViewSet` o cambiar a client-side
- [ ] **Opcional - Advertencia #4:** Verificar y actualizar sintaxis de Bootstrap si es necesario

### Después de Correcciones:

- [ ] Ejecutar `python manage.py check` (sin errores)
- [ ] Ejecutar `python manage.py migrate_schemas --tenant` (si hay migraciones pendientes)
- [ ] Ejecutar pruebas de humo según el plan (TEST 1-5)
- [ ] Verificar logs del servidor durante las pruebas (sin errores 500)

---

## 📚 REFERENCIAS

- **Modelos:** `apps/tenant/inventario/models.py`
- **Serializers:** `apps/tenant/inventario/api/serializers.py`
- **ViewSets:** `apps/tenant/inventario/api/viewsets.py`
- **Services:** `apps/tenant/inventario/services.py`
- **URLs:** `apps/tenant/inventario/api/urls.py`
- **Frontend API:** `apps/tenant/core/static/core/js/inventario/inventario.api.js`
- **Frontend Pages:** `apps/tenant/core/static/core/js/inventario/*.page.js`

---

**Documento generado:** 2024  
**Última actualización:** Tras refactorización completa del módulo de Inventario v2.40
