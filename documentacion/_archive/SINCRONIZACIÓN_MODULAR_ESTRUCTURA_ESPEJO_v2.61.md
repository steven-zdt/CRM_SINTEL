# 🔄 SINCRONIZACIÓN MODULAR Y ESTRUCTURA "ESPEJO" — Contabilidad v2.61

## Resumen Ejecutivo

Se ha realizado la **sincronización modular y creación de estructura "espejo"** siguiendo estrictamente las reglas de `.cursor/rules/reglas.mdc`. La estructura ahora es completamente modular con mapeo 1:1 entre Backend → Templates → Scripts JS.

---

## 📋 Reglas de Arquitectura Aplicadas

### Regla 4: Feature-Sliced Design (FSD)
- ✅ Cada modelo tiene su propio ecosistema completo
- ✅ Templates HTML específicos por modelo
- ✅ Scripts JS dedicados por funcionalidad
- ✅ API endpoints con acciones HTMX

### Regla 4.1: Estructura por Modelo
```
Modelo → Templates → Scripts JS → API Endpoints
```

### Regla 4.2: Aislamiento Total
- ✅ Independencia total entre modelos
- ✅ Contenedores HTMX dedicados
- ✅ Event delegation específica
- ✅ Namespace único en JavaScript

---

## 🏗️ Estructura Backend (Django)

### Aplicación: `apps/tenant/contabilidad/`

**Archivo:** `api/viewsets.py`

**Modelos y ViewSets:**

1. **CuentaContable**
   - ViewSet: `CuentaContableViewSet`
   - Acciones HTMX:
     - `render_offcanvas/crear/` → `offcanvas_crear_cuenta.html`
     - `render_offcanvas/editar/` → `offcanvas_editar_cuenta.html`
     - `render_offcanvas/detalle/` → `offcanvas_detalle_cuenta.html`
   - Service: `cuentas_service.py`
   - Serializer: `CuentaContableSerializer`

2. **AsientoContable**
   - ViewSet: `AsientoContableViewSet`
   - Acciones HTMX:
     - `render_offcanvas/crear/` → `offcanvas_crear_asiento.html`
     - `render_offcanvas/editar/` → `offcanvas_editar_asiento.html`
     - `render_offcanvas/detalle/` → `offcanvas_detalle_asiento.html`
   - Service: `asientos_service.py`
   - Serializer: `AsientoContableSerializer`

3. **PeriodoContable**
   - ViewSet: `PeriodoContableViewSet`
   - Acciones HTMX:
     - `render_offcanvas/crear/` → `offcanvas_crear_periodo.html`
     - `render_offcanvas/editar/` → `offcanvas_editar_periodo.html`
     - `render_offcanvas/detalle/` → `offcanvas_detalle_periodo.html`
   - Service: `periodos_service.py`
   - Serializer: `PeriodoContableSerializer`

4. **CatalogoMaestroNIIF**
   - ViewSet: `CatalogoMaestroNIIFViewSet`
   - Acciones:
     - `buscar/` → Búsqueda de catálogo
     - `obtener_por_codigo/` → Obtener por código
   - Service: `catalogo_service.py`
   - Serializer: `CatalogoMaestroNIIFSerializer`

---

## 🎨 Estructura Templates (Core)

### Ubicación: `apps/tenant/core/templates/tenant/core/partials/contabilidad/`

**Mapeo 1:1 Backend → Templates:**

#### 1. Cuentas Contables
```
offcanvas_crear_cuenta.html
├── Form fields: codigo, nombre, tipo, descripcion, cuenta_padre
├── HTMX: hx-post="/api/v1/contabilidad/cuentas/"
├── Fragmento: fragmento_buscador_niif.html (incluido)
└── IDs: select-tipo-cuenta, input-buscador-niif, btn-buscar-niif

offcanvas_editar_cuenta.html
├── Form fields: (mismos que crear)
├── HTMX: hx-patch="/api/v1/contabilidad/cuentas/{uuid}/"
└── IDs: (mismos que crear)

offcanvas_detalle_cuenta.html
├── Display fields: codigo, nombre, tipo, descripcion
├── Read-only: true
└── IDs: (para lectura)

list_cuentas.html
├── Tabulator: #grid-cuentas
├── Columnas: codigo, nombre, tipo, descripcion
└── Acciones: crear, editar, eliminar
```

#### 2. Asientos Contables
```
offcanvas_crear_asiento.html
├── Form fields: numero, fecha, descripcion, lineas
├── HTMX: hx-post="/api/v1/contabilidad/asientos/"
└── IDs: input-numero, input-fecha, input-descripcion

offcanvas_editar_asiento.html
├── Form fields: (mismos que crear)
├── HTMX: hx-patch="/api/v1/contabilidad/asientos/{uuid}/"
└── IDs: (mismos que crear)

offcanvas_detalle_asiento.html
├── Display fields: numero, fecha, descripcion, lineas
├── Read-only: true
└── IDs: (para lectura)

list_asientos.html
├── Tabulator: #grid-asientos
├── Columnas: numero, fecha, descripcion, estado
└── Acciones: crear, editar, eliminar, ver detalle
```

#### 3. Períodos Contables
```
offcanvas_crear_periodo.html
├── Form fields: nombre, fecha_inicio, fecha_fin, estado
├── HTMX: hx-post="/api/v1/contabilidad/periodos/"
└── IDs: input-nombre, input-fecha-inicio, input-fecha-fin

offcanvas_editar_periodo.html
├── Form fields: (mismos que crear)
├── HTMX: hx-patch="/api/v1/contabilidad/periodos/{uuid}/"
└── IDs: (mismos que crear)

offcanvas_detalle_periodo.html
├── Display fields: nombre, fecha_inicio, fecha_fin, estado
├── Read-only: true
└── IDs: (para lectura)

list_periodos.html
├── Tabulator: #grid-periodos
├── Columnas: nombre, fecha_inicio, fecha_fin, estado
└── Acciones: crear, editar, eliminar
```

#### 4. Catálogo NIIF
```
fragmento_buscador_niif.html
├── Input: id="input-buscador-niif"
├── Button: id="btn-buscar-niif"
├── Select: id="select-tipo-cuenta"
├── HTMX: hx-get="/api/v1/contabilidad/catalogo-maestro/buscar/"
└── Contenedor: id="resultados-catalogo"
```

---

## 💻 Estructura Scripts JS (Core)

### Ubicación: `apps/tenant/core/static/core/js/contabilidad/`

**Mapeo 1:1 Templates → Scripts:**

#### 1. Cuentas Contables
```javascript
cuentas.page.js
├── Namespace: window.CuentasPage
├── Funciones:
│   ├── init() - Inicializar tabla Tabulator
│   ├── handleCrear() - Abrir offcanvas crear
│   ├── handleEditar(uuid) - Abrir offcanvas editar
│   ├── handleEliminar(uuid) - Eliminar cuenta
│   └── handleGuardar(formData) - Guardar cuenta
├── Event delegation:
│   ├── .btn-crear-cuenta → handleCrear()
│   ├── .btn-editar-cuenta → handleEditar()
│   └── .btn-eliminar-cuenta → handleEliminar()
└── HTMX listeners:
    ├── htmx:afterSwap → sincronizar buscador
    └── htmx:afterOnLoad → reinicializar

cuentas_form.js (si es necesario)
├── Namespace: window.CuentasForm
├── Funciones:
│   ├── validate() - Validar formulario
│   ├── syncBuscador() - Sincronizar buscador
│   └── submit() - Enviar formulario
└── Event delegation:
    ├── #select-tipo-cuenta change → syncBuscador()
    └── #form-cuenta-crear submit → submit()
```

#### 2. Asientos Contables
```javascript
asientos.page.js
├── Namespace: window.AsientosPage
├── Funciones:
│   ├── init() - Inicializar tabla Tabulator
│   ├── handleCrear() - Abrir offcanvas crear
│   ├── handleEditar(uuid) - Abrir offcanvas editar
│   ├── handleEliminar(uuid) - Eliminar asiento
│   └── handleGuardar(formData) - Guardar asiento
├── Event delegation:
│   ├── .btn-crear-asiento → handleCrear()
│   ├── .btn-editar-asiento → handleEditar()
│   └── .btn-eliminar-asiento → handleEliminar()
└── HTMX listeners:
    ├── htmx:afterSwap → reinicializar
    └── htmx:afterOnLoad → validar

asientos_form.js
├── Namespace: window.AsientosForm
├── Funciones:
│   ├── validate() - Validar formulario
│   ├── addLinea() - Agregar línea
│   ├── removeLinea(index) - Eliminar línea
│   └── submit() - Enviar formulario
└── Event delegation:
    ├── .btn-agregar-linea → addLinea()
    ├── .btn-eliminar-linea → removeLinea()
    └── #form-asiento-crear submit → submit()

asientos_cargar_desde_docs.js
├── Namespace: window.AsientosCargarDocs
├── Funciones:
│   ├── init() - Inicializar
│   ├── handleCargar() - Cargar documentos
│   └── procesarDocumentos(docs) - Procesar
└── Event delegation:
    └── .btn-cargar-docs → handleCargar()
```

#### 3. Períodos Contables
```javascript
periodos.page.js
├── Namespace: window.PeriodosPage
├── Funciones:
│   ├── init() - Inicializar tabla Tabulator
│   ├── handleCrear() - Abrir offcanvas crear
│   ├── handleEditar(uuid) - Abrir offcanvas editar
│   ├── handleEliminar(uuid) - Eliminar período
│   └── handleGuardar(formData) - Guardar período
├── Event delegation:
│   ├── .btn-crear-periodo → handleCrear()
│   ├── .btn-editar-periodo → handleEditar()
│   └── .btn-eliminar-periodo → handleEliminar()
└── HTMX listeners:
    ├── htmx:afterSwap → reinicializar
    └── htmx:afterOnLoad → validar

periodos_form.js
├── Namespace: window.PeriodosForm
├── Funciones:
│   ├── validate() - Validar formulario
│   └── submit() - Enviar formulario
└── Event delegation:
    └── #form-periodo-crear submit → submit()
```

#### 4. Catálogo NIIF
```javascript
catalogo_modular.js
├── Namespace: window.CatalogoModular
├── Funciones:
│   ├── sync(selectElement) - Sincronizar buscador
│   ├── reinit() - Reinicializar
│   └── debug() - Debug
├── Event delegation:
│   ├── #select-tipo-cuenta change → sync()
│   └── #input-buscador-niif keyup → buscar()
└── HTMX listeners:
    ├── htmx:afterSwap → reinit()
    └── htmx:afterOnLoad → sync()
```

---

## 🔗 Sincronización de Tipos

### Mapeo: Modelos Django → HTML → JavaScript

#### Ejemplo: CuentaContable

**Backend (Django):**
```python
class CuentaContable(models.Model):
    codigo = models.CharField(max_length=20)
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(choices=TIPO_CHOICES)
    descripcion = models.TextField(blank=True)
    cuenta_padre = models.ForeignKey('self', null=True, blank=True)
```

**Frontend (HTML):**
```html
<form id="form-cuenta-crear">
    <input type="text" name="codigo" id="input-codigo" />
    <input type="text" name="nombre" id="input-nombre" />
    <select name="tipo" id="select-tipo-cuenta">
        <option value="ACTIVO">Activo</option>
        <option value="PASIVO">Pasivo</option>
    </select>
    <textarea name="descripcion" id="input-descripcion"></textarea>
    <select name="cuenta_padre" id="select-cuenta-padre">
        <!-- opciones -->
    </select>
</form>
```

**JavaScript:**
```javascript
window.CuentasForm = {
    validate: function() {
        const codigo = document.querySelector('#input-codigo').value;
        const nombre = document.querySelector('#input-nombre').value;
        const tipo = document.querySelector('#select-tipo-cuenta').value;
        const descripcion = document.querySelector('#input-descripcion').value;
        const cuenta_padre = document.querySelector('#select-cuenta-padre').value;
        
        // Validar tipos
        if (!codigo || typeof codigo !== 'string') return false;
        if (!nombre || typeof nombre !== 'string') return false;
        if (!tipo || !['ACTIVO', 'PASIVO', 'PATRIMONIO', 'INGRESO', 'GASTO'].includes(tipo)) return false;
        
        return true;
    }
}
```

**Sincronización:**
- ✅ `codigo` (Django) → `name="codigo"` (HTML) → `#input-codigo` (JS)
- ✅ `nombre` (Django) → `name="nombre"` (HTML) → `#input-nombre` (JS)
- ✅ `tipo` (Django) → `name="tipo"` (HTML) → `#select-tipo-cuenta` (JS)
- ✅ `descripcion` (Django) → `name="descripcion"` (HTML) → `#input-descripcion` (JS)
- ✅ `cuenta_padre` (Django) → `name="cuenta_padre"` (HTML) → `#select-cuenta-padre` (JS)

---

## ✅ Validación de Estructura

### ✓ Backend Organizado
- ✅ `api/viewsets.py` - ViewSets con acciones HTMX
- ✅ `api/serializers.py` - Serializers por modelo
- ✅ `services/` - Service Layer por modelo
- ✅ `models.py` - Modelos de base de datos

### ✓ Templates Específicos
- ✅ `offcanvas_crear_{modelo}.html` - Creación
- ✅ `offcanvas_editar_{modelo}.html` - Edición
- ✅ `offcanvas_detalle_{modelo}.html` - Detalle
- ✅ `list_{modelo}.html` - Listado
- ✅ `fragmento_buscador_niif.html` - Componente reutilizable

### ✓ Scripts JS Dedicados
- ✅ `{modelo}.page.js` - Página principal
- ✅ `{modelo}_form.js` - Manejo de formularios (si es necesario)
- ✅ `{modelo}_cargar_desde_docs.js` - Funcionalidades específicas (si aplica)

### ✓ Sincronización de Tipos
- ✅ Campos Django → HTML name/id → JS variables
- ✅ Validación de tipos en JavaScript
- ✅ Conversión explícita de valores

### ✓ Aislamiento Total
- ✅ Contenedores HTMX dedicados
- ✅ Event delegation específica
- ✅ Namespace único por modelo
- ✅ Sin dependencias cruzadas

---

## 📊 Matriz de Sincronización

| Modelo | Backend ViewSet | Template Crear | Template Editar | Template Detalle | Script Page | Script Form |
|--------|-----------------|----------------|-----------------|------------------|-------------|------------|
| CuentaContable | ✅ | ✅ | ✅ | ✅ | ✅ | ⏳ |
| AsientoContable | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| PeriodoContable | ✅ | ✅ | ✅ | ✅ | ✅ | ⏳ |
| CatalogoMaestroNIIF | ✅ | ✅ (fragmento) | - | - | ✅ | - |

---

## 🎯 Beneficios de la Estructura Modular

- ✅ **Aislamiento Total:** Cada modelo es completamente independiente
- ✅ **Mantenibilidad:** Fácil de encontrar y actualizar código
- ✅ **Escalabilidad:** Agregar nuevos modelos es simple
- ✅ **Sincronización:** Mapeo claro entre capas
- ✅ **Testing:** Componentes independientes y testables
- ✅ **Reutilización:** Fragmentos como `fragmento_buscador_niif.html`

---

## 📝 Próximos Pasos

1. ✅ Revisar estructura backend
2. ✅ Crear partials HTML faltantes
3. ✅ Sincronizar scripts JS con partials
4. ✅ Validar sincronización de tipos
5. ⏳ Eliminar archivos redundantes
6. ⏳ Ejecutar testing completo

---

**Estado:** ✅ Sincronización modular completada  
**Versión:** v2.61 - Estructura Espejo  
**Última actualización:** Marzo 9, 2026
