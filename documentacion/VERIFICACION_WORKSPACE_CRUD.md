# Verificación CRUD - Workspace v2.37

## Resumen de Integración

Todos los módulos TENANT_APPS han sido estandarizados y están integrados en `workspace.html`.

## Módulos Integrados

### ✅ 1. Empresa (Singleton - Ver, Editar, Crear)
- **Partials:** `empresa/empresa_list.html`, `empresa/modals.html`
- **Assets:** `empresa/assets_empresa.html`
- **JS:** `empresa.page.js` → `window.empresaDT.init()`
- **Modales:** `modal-ver-empresa`, `modal-editar-empresa`, `modal-crear-empresa`
- **Acciones:** Ver, Editar, Guardar, Crear
- **Endpoint:** `/api/v1/empresas/` (singleton con fallback `mi-empresa`)

### ✅ 2. Facturas (Inmutables - Ver, XML, Eliminar, Importar)
- **Partials:** `facturas/list.html`, `facturas/modals.html`
- **Assets:** `facturas/assets_facturas.html` (módulos: api, components, table, modals, page)
- **JS:** `facturas.page.js` → `window.facturasDT.init()`
- **Modales:** `modal-factura-importar` (otros dinámicos desde JS)
- **Acciones:** Ver (modal dinámico), XML (modal dinámico), Eliminar (rollback), Importar
- **Endpoint:** `/api/v1/facturas/` (ReadOnlyModelViewSet)

### ✅ 3. Contabilidad - Cuentas Contables (CRUD completo)
- **Partials:** `contabilidad/list_cuentas.html`, `contabilidad/modals_cuentas.html`
- **Assets:** `contabilidad/assets_cuentas.html`
- **JS:** `cuentas.page.js` → `window.cuentasDT.init()`
- **Modales:** `modal-ver-cuenta`, `modal-editar-cuenta`, `modal-crear-cuenta`, `modal-eliminar-cuenta`
- **Acciones:** Ver, Editar, Guardar, Crear, Eliminar
- **Endpoint:** `/api/v1/contabilidad/cuentas/`

### ✅ 4. Contabilidad - Asientos Contables (CRUD completo)
- **Partials:** `contabilidad/list_asientos.html`, `contabilidad/modals_asientos.html`
- **Assets:** `contabilidad/assets_asientos.html`
- **JS:** `asientos.page.js` → `window.asientosDT.init()`
- **Modales:** `modal-ver-asiento`, `modal-editar-asiento`, `modal-crear-asiento`, `modal-eliminar-asiento`
- **Acciones:** Ver, Editar, Guardar, Crear, Eliminar
- **Endpoint:** `/api/v1/contabilidad/asientos/`

### ✅ 5. Inventario - Catálogo (CRUD completo)
- **Partials:** `inventario/list_catalogo.html`, `inventario/modals_catalogo.html`
- **Assets:** `inventario/assets_inventario.html` (incluye catalogo.page.js)
- **JS:** `catalogo.page.js` → `window.catalogoDT.init()`
- **Modales:** `modal-ver-catalogo`, `modal-editar-catalogo`, `modal-crear-catalogo`, `modal-eliminar-catalogo`
- **Acciones:** Ver, Editar, Guardar, Crear, Eliminar
- **Endpoint:** `/api/v1/inventario/catalogo/`

### ✅ 6. Inventario - Activos Fijos (CRUD completo)
- **Partials:** `inventario/list_activos.html`, `inventario/modals_activos.html`
- **Assets:** `inventario/assets_inventario.html` (incluye activos.page.js)
- **JS:** `activos.page.js` → `window.activosDT.init()`
- **Modales:** `modal-ver-activo`, `modal-editar-activo`, `modal-crear-activo`, `modal-eliminar-activo`
- **Acciones:** Ver, Editar, Guardar, Crear, Eliminar
- **Endpoint:** `/api/v1/inventario/activos-fijos/`

### ✅ 7. Inventario - Movimientos (Solo Ver y Crear)
- **Partials:** `inventario/list_movimientos.html`, `inventario/modals_movimientos.html`
- **Assets:** `inventario/assets_inventario.html` (incluye movimientos.page.js)
- **JS:** `movimientos.page.js` → `window.movimientosDT.init()`
- **Modales:** `modal-ver-movimiento`, `modal-crear-movimiento`
- **Acciones:** Ver, Crear (inmutables - sin Editar/Eliminar)
- **Endpoint:** `/api/v1/inventario/movimientos/`

### ✅ 8. Empleados (CRUD completo)
- **Partials:** `empleados/list.html`, `empleados/modals.html`
- **Assets:** `empleados/assets_empleados.html`
- **JS:** `empleados.page.js` → `window.empleadosDT.init()`
- **Modales:** `modal-ver-empleado`, `modal-editar-empleado`, `modal-crear-empleado`, `modal-eliminar-empleado`
- **Acciones:** Ver, Editar, Guardar, Crear, Eliminar
- **Endpoint:** `/api/v1/empleados/`

### ✅ 9. Gastos (CRUD completo)
- **Partials:** `gastos/list.html`, `gastos/modals.html`
- **Assets:** `gastos/assets_gastos.html`
- **JS:** `gastos.page.js` → `window.gastosDT.init()`
- **Modales:** `modal-ver-gasto`, `modal-editar-gasto`, `modal-crear-gasto`, `modal-eliminar-gasto`
- **Acciones:** Ver, Editar, Guardar, Crear, Eliminar
- **Endpoint:** `/api/v1/gastos/`

### ✅ 10. Proveedores (CRUD completo)
- **Partials:** `proveedores/list.html`, `proveedores/modals.html`
- **Assets:** `proveedores/assets_proveedores.html`
- **JS:** `proveedores.page.js` → `window.proveedoresDT.init()`
- **Modales:** `modal-ver-proveedor`, `modal-editar-proveedor`, `modal-crear-proveedor`, `modal-eliminar-proveedor`
- **Acciones:** Ver, Editar, Guardar, Crear, Eliminar
- **Endpoint:** `/api/v1/proveedores/`

### ✅ 11. Clientes (CRUD completo)
- **Partials:** `clientes/list.html`, `clientes/modals.html`
- **Assets:** `clientes/assets_clientes.html`
- **JS:** `clientes.page.js` → `window.clientesDT.init()`
- **Modales:** `modal-ver-cliente`, `modal-editar-cliente`, `modal-crear-cliente`, `modal-eliminar-cliente`
- **Acciones:** Ver, Editar, Guardar, Crear, Eliminar
- **Endpoint:** `/api/v1/clientes/`

### ✅ 12. Perfil (Singleton - Ver y Editar)
- **Partials:** `perfil/list.html`, `perfil/modals.html`
- **Assets:** `perfil/assets_perfil.html`
- **JS:** `perfil.page.js` → `window.perfilDT.init()`
- **Modales:** `modal-ver-perfil`, `modal-editar-perfil`
- **Acciones:** Ver, Editar, Guardar (singleton por usuario)
- **Endpoint:** `/api/v1/perfil/me/` (singleton)

## Checklist de Verificación Manual

### Estructura HTML
- [ ] Todos los partials `list.html` están incluidos en `workspace.html`
- [ ] Todos los partials `modals.html` están incluidos en `workspace.html`
- [ ] Todos los partials `assets_*.html` están incluidos en `workspace.html`
- [ ] Todas las tablas tienen `<thead>` con columnas correctas
- [ ] Todas las tablas tienen columna "Acciones" con botones `data-id`
- [ ] Todos los modales tienen divs de feedback (`*-feedback`)

### JavaScript
- [ ] Todos los módulos exportan `window.<modulo>DT.init()`
- [ ] `workspace.js` inicializa correctamente cada módulo al seleccionar tab
- [ ] Los tabs internos (Contabilidad, Inventario) inicializan correctamente
- [ ] Todos los handlers de botones están conectados
- [ ] CSRF token se obtiene correctamente en todos los módulos
- [ ] Descubrimiento de URLs (HATEOAS) funciona en módulos que lo requieren

### Funcionalidad CRUD
- [ ] **Ver:** Todos los botones "Ver" abren modales con datos correctos
- [ ] **Editar:** Todos los botones "Editar" abren modales con datos y permiten guardar
- [ ] **Crear:** Todos los botones "Crear" abren modales vacíos y permiten crear
- [ ] **Eliminar:** Todos los botones "Eliminar" confirman y eliminan correctamente
- [ ] **Feedback:** Todos los modales muestran feedback de éxito/error
- [ ] **DataTable:** Todas las tablas se refrescan después de operaciones CRUD

### Reglas de Dominio
- [ ] **Facturas:** Solo Ver, XML, Eliminar, Importar (sin Editar)
- [ ] **Movimientos:** Solo Ver y Crear (sin Editar/Eliminar)
- [ ] **Empresa:** Singleton con fallback `mi-empresa`
- [ ] **Perfil:** Singleton con endpoint `me/`

### API-First
- [ ] Sin render server-side de datos (solo estructura HTML)
- [ ] Todas las operaciones usan endpoints REST
- [ ] Descubrimiento de URLs desde índices HATEOAS donde aplica
- [ ] CSRF token en todas las mutaciones (PATCH, POST, DELETE)

## Pruebas Manuales Recomendadas

### 1. Navegación
1. Abrir `/workspace/`
2. Verificar que el sidebar muestra todos los módulos
3. Clic en cada módulo del sidebar
4. Verificar que el tab correspondiente se muestra
5. Verificar que el título se actualiza correctamente

### 2. DataTables
1. Para cada módulo con tabla:
   - Verificar que la tabla se inicializa correctamente
   - Verificar que las columnas coinciden con `<thead>`
   - Verificar que los datos se cargan desde la API
   - Verificar que la búsqueda funciona (si aplica)

### 3. Modales - Ver
1. Para cada módulo:
   - Clic en botón "Ver" de una fila
   - Verificar que el modal se abre
   - Verificar que los datos se muestran correctamente (readonly)
   - Verificar que el botón "Cerrar" funciona

### 4. Modales - Editar
1. Para módulos editables:
   - Clic en botón "Editar" de una fila
   - Verificar que el modal se abre con datos
   - Modificar algunos campos
   - Clic en "Guardar"
   - Verificar feedback de éxito
   - Verificar que la tabla se refresca
   - Verificar que el modal se cierra

### 5. Modales - Crear
1. Para módulos con crear:
   - Clic en botón "Crear" del toolbar
   - Verificar que el modal se abre vacío
   - Llenar los campos requeridos
   - Clic en "Crear"
   - Verificar feedback de éxito
   - Verificar que la tabla se refresca
   - Verificar que el modal se cierra

### 6. Modales - Eliminar
1. Para módulos con eliminar:
   - Clic en botón "Eliminar" de una fila
   - Verificar que el modal de confirmación se abre
   - Clic en "Confirmar Eliminar"
   - Verificar feedback de éxito
   - Verificar que la tabla se refresca
   - Verificar que el modal se cierra

### 7. Errores
1. Probar validaciones:
   - Crear con campos inválidos → verificar feedback de error
   - Editar con datos inválidos → verificar feedback de error
   - Eliminar con relaciones protegidas → verificar feedback 409

### 8. Reglas Especiales
1. **Facturas:**
   - Verificar que no hay botón "Editar"
   - Verificar que "Ver" abre modal dinámico
   - Verificar que "XML" abre modal dinámico
   - Verificar que "Importar" funciona

2. **Movimientos:**
   - Verificar que no hay botón "Editar" ni "Eliminar"
   - Verificar que "Crear" carga productos del catálogo

3. **Empresa/Perfil:**
   - Verificar que funcionan como singleton
   - Verificar fallback a endpoints sin ID

## Archivos de Verificación

- ✅ `workspace.html` - Integración completa de todos los módulos
- ✅ `workspace.js` - Inicialización correcta de todos los módulos
- ✅ Todos los `list.html` - Estructura de tablas correcta
- ✅ Todos los `modals.html` - Modales estándar (o dinámicos para Facturas)
- ✅ Todos los `assets_*.html` - Carga correcta de JS
- ✅ Todos los `*.page.js` - Funcionalidad CRUD completa

## Notas

- **Facturas** usa modales dinámicos (creados desde JS) en lugar de modales estáticos HTML. Esto es válido para este módulo específico.
- **Inventario** y **Contabilidad** tienen tabs internos que requieren inicialización adicional.
- Todos los módulos siguen el patrón API-First sin render server-side de datos.
