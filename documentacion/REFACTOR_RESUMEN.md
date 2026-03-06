# Resumen de Refactorización UUID + API Unificada

## ✅ Completado

### 1. Módulo Centralizado de API Helpers
- **Archivo:** `apps/tenant/core/static/core/js/lib/api.js`
- **Funciones:** `buildDetailUrl`, `safeFetchJson`, `getEntityKeyFromRow`, `assertValidKey`, `mapResponsabilidadesToCodes`
- **URLs base:** `API.empresas`, `API.cuentas`, `API.asientos`, etc.
- **Export:** `window.API_HELPERS`

### 2. ViewSet Base con UUID
- **Archivo:** `apps/tenant/api/base.py`
- **Clase:** `BaseTenantViewSet` con `lookup_field="uuid"`

### 3. Ejemplo Completo: CuentaContable
- ✅ Modelo: Campo `uuid` agregado
- ✅ ViewSet: Hereda de `BaseTenantViewSet`
- ✅ Services: `uuid` incluido en `CUENTA_LIST_FIELDS` y `CUENTA_DETAIL_FIELDS`
- ✅ Router: `trailing_slash=True` configurado
- ⚠️ **Pendiente:** Migración de datos y refactorización de JS

### 4. Documentación
- `REFACTOR_UUID_PLAN.md` - Plan completo de refactorización
- `REFACTOR_EJEMPLO_CUENTAS.md` - Ejemplo detallado para CuentaContable

## ⚠️ Pendiente

### Backend

1. **Migraciones:**
   - [ ] Crear migración para agregar `uuid` a `CuentaContable`
   - [ ] Crear migración de backfill para `CuentaContable`
   - [ ] Repetir para `AsientoContable` y todos los demás modelos

2. **Modelos (agregar campo uuid):**
   - [ ] `AsientoContable` ✅ (código agregado, falta migración)
   - [ ] `Empleado`
   - [ ] `Gasto`
   - [ ] `Proveedor`
   - [ ] `Cliente`
   - [ ] `CatalogoItem`
   - [ ] `ActivoFijo`
   - [ ] `MovimientoInventario`
   - [ ] `Empresa` (opcional, singleton)
   - [ ] Otros modelos con ViewSets de detalle

3. **ViewSets (heredar de BaseTenantViewSet):**
   - [x] `CuentaContableViewSet` ✅
   - [x] `AsientoContableViewSet` ✅
   - [ ] `EmpleadoViewSet`
   - [ ] `GastoViewSet`
   - [ ] `ProveedorViewSet`
   - [ ] `ClienteViewSet`
   - [ ] `CatalogoItemViewSet`
   - [ ] `ActivoFijoViewSet`
   - [ ] `MovimientoInventarioViewSet`
   - [ ] `EmpresaViewSet` (singleton, puede mantener id)
   - [ ] Otros ViewSets

4. **Serializers (incluir uuid):**
   - [ ] Todos los `*ListSerializer` deben incluir `uuid`
   - [ ] Todos los `*DetailSerializer` deben incluir `uuid`

5. **Routers (unificar trailing_slash):**
   - [x] `apps/tenant/contabilidad/api/urls.py` ✅
   - [ ] `apps/tenant/empleados/api/urls.py`
   - [ ] `apps/tenant/gastos/api/urls.py`
   - [ ] `apps/tenant/proveedores/api/urls.py`
   - [ ] `apps/tenant/clientes/api/urls.py`
   - [ ] `apps/tenant/inventario/api/urls.py`
   - [ ] `apps/tenant/empresa/api/urls.py`
   - [ ] Todos los demás routers

6. **Empresa - Responsabilidades RUT:**
   - [ ] Crear endpoint `/api/v1/empresas/responsabilidades-rut-choices/`
   - [ ] Actualizar serializer para validar códigos
   - [ ] Refactorizar JS para mapear selecciones a códigos

### Frontend

1. **Incluir api.js:**
   - [ ] Agregar `<script src="{% static 'core/js/lib/api.js' %}"></script>` en `workspace.html`

2. **Refactorizar *.page.js:**
   - [ ] `cuentas.page.js` - Usar helpers centralizados y uuid
   - [ ] `asientos.page.js` - Usar helpers centralizados y uuid
   - [ ] `empleados.page.js` - Usar helpers centralizados y uuid
   - [ ] `gastos.page.js` - Usar helpers centralizados y uuid
   - [ ] `proveedores.page.js` - Usar helpers centralizados y uuid
   - [ ] `clientes.page.js` - Usar helpers centralizados y uuid
   - [ ] `catalogo.page.js` - Usar helpers centralizados y uuid
   - [ ] `activos.page.js` - Usar helpers centralizados y uuid
   - [ ] `movimientos.page.js` - Usar helpers centralizados y uuid
   - [ ] `empresa.page.js` - Usar helpers centralizados y mapear responsabilidades
   - [ ] Otros archivos JS

3. **Eliminar IDs hardcodeados:**
   - [ ] Buscar y reemplazar `id = 1`, `data-id="1"`, etc.
   - [ ] Cambiar `data-id` por `data-uuid` en botones
   - [ ] Cambiar `dataset.id` por `dataset.uuid` en handlers

## Orden de Ejecución Recomendado

1. **Fase 1: Backend Base** (1-2 horas)
   - Crear migraciones para `CuentaContable` y `AsientoContable`
   - Aplicar migraciones
   - Verificar que los endpoints funcionan con UUID

2. **Fase 2: Frontend Ejemplo** (1 hora)
   - Incluir `api.js` en `workspace.html`
   - Refactorizar `cuentas.page.js` completamente
   - Probar end-to-end

3. **Fase 3: Replicar Patrón** (4-6 horas)
   - Aplicar el mismo patrón a todos los demás módulos
   - Crear migraciones en batch
   - Refactorizar JS en batch

4. **Fase 4: Empresa Especial** (1 hora)
   - Endpoint de choices
   - Mapeo de responsabilidades
   - Validación mejorada

5. **Fase 5: Testing** (1-2 horas)
   - Tests de API con UUID
   - Tests de frontend
   - Verificación manual

## Comandos Útiles

```bash
# Crear migraciones
python manage.py makemigrations contabilidad
python manage.py makemigrations empleados
# ... para cada app

# Aplicar migraciones
python manage.py migrate

# Verificar rutas
python manage.py show_urls | grep api/v1

# Buscar IDs hardcodeados en JS
grep -r "id = 1" apps/tenant/core/static/core/js/
grep -r 'data-id="1"' apps/tenant/core/static/core/js/
```

## Notas Importantes

1. **Compatibilidad:** Durante la transición, mantener soporte para `id` como fallback
2. **Migraciones:** Asegurar que el backfill de UUIDs no rompa datos existentes
3. **Testing:** Probar cada módulo después de refactorizar
4. **Rollback:** Mantener backups antes de aplicar migraciones masivas
