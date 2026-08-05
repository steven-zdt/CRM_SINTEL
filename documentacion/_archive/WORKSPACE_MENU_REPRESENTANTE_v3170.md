# Workspace Menú Representante v3.17.0

**Fecha:** 2026-06-10  
**Versión:** v3.17.0  
**Estado:** ✅ MENU AGREGADO

---

## 📍 Ubicación en Workspace

```
URL: http://localhost:8000/workspace/#proveedores
```

---

## 🎯 Estructura de Menú

### Menú Lateral (Sidebar)
```
├── Dashboard
├── Empresa
├── Proyectos
├── Facturas
├── Contabilidad
├── Inventario
├── Clientes
├── Proveedores  ← AQUI (actualizado v3.17.0)
├── Empleados
├── Cotizaciones
├── Gastos
├── Bancos
└── Mi Perfil
```

### Sub-tabs dentro de Proveedores (NUEVO v3.17.0)
```
┌─────────────────────────────────────────────────────────┐
│  🚚 Directorio de Proveedores  📊 Cuentas por Pagar   │ 👥 Representantes  │
└─────────────────────────────────────────────────────────┘
                           ↓
        ┌─────────────────────────────────┐
        │  TAB 1: Directorio (active)     │
        │  - Grid de proveedores          │
        │  - Acciones: Editar/Eliminar   │
        └─────────────────────────────────┘

        ┌─────────────────────────────────┐
        │  TAB 2: Cuentas por Pagar       │
        │  - Info: "Ver en detalle de     │
        │    cada proveedor"              │
        └─────────────────────────────────┘

        ┌─────────────────────────────────┐
        │  TAB 3: Representantes (NEW)    │
        │  - Grid consolidado             │
        │  - Todos los representantes     │
        │  - Búsqueda global              │
        │  - Acciones: Editar/Eliminar   │
        └─────────────────────────────────┘
```

---

## ✨ Características del Tab Representantes

### Vista
- **Grid Tabulator** con columnas:
  1. **Documento**: Número + Tipo (CC/CE/PA/NIT)
  2. **Nombre Completo**: Nombre + badge "Principal" (si aplica)
  3. **Cargo**: Título/rol en la organización
  4. **Email/Teléfono**: Información de contacto
  5. **Acciones**: Editar (lápiz) / Eliminar (papelera)

### Búsqueda
- Input de búsqueda integrado en header
- Busca en: nombre, documento, email
- Search en tiempo real (keyup listener)

### Paginación
- Tabulator local pagination
- 20 registros por página (configurable: 10, 20, 50, 100)
- Sorting local habilitado

### Lazy-Load
- Tab se carga solo al hacer click
- No consume recursos hasta que se necesita
- Event listener en `shown.bs.tab`

---

## 🔄 Flujos de Interacción

### Flujo 1: Ver Directorio
1. Click en menú **Proveedores**
2. Tab **"Directorio de Proveedores"** abre (default)
3. Ver lista de proveedores

### Flujo 2: Ver Representantes
1. Click en menú **Proveedores**
2. Click en tab **"Representantes"** ⭐
3. Grid carga con todos los representantes
4. Buscar por nombre/documento/email
5. Click lápiz → Editar
6. Click papelera → Eliminar (con confirm)

### Flujo 3: Crear Representante desde Directorio
1. Estar en tab **"Representantes"**
2. Click en fila de representante
3. Offcanvas abre en modo **EDITAR**
4. Modificar campos
5. Click "Guardar"
6. Grid se recarga

### Flujo 4: Crear Representante desde Detalle
1. Ir a **Directorio** → Click proveedor (row click)
2. Offcanvas detalle abre
3. Click tab **"Representantes"** (dentro del detalle)
4. Click "+ Agregar Representante"
5. Offcanvas form abre
6. Llenar datos
7. Click "Guardar"
8. Tabla dentro del detalle se recarga

---

## 🗂️ Archivos Modificados/Creados

### Modificados
1. **workspace.html** (core)
   - Agregados 3 sub-tabs en sección proveedores
   - Agregado contenedor offcanvas

2. **proveedores_main.js**
   - Actualizado initSubtabRedraws() para 3 tabs
   - Agregado soporte Representantes tab

### Creados
1. **representantes_directory.html** (nuevo partial)
   - Grid Tabulator consolidado
   - JavaScript inline para tabulator init
   - Search + pagination + sorting
   - Event listeners editar/eliminar

---

## 🧪 Testing Checklist

- [ ] Click menú Proveedores → abre directorio (tab 1)
- [ ] Click tab "Representantes" → grid carga (vacío o con datos)
- [ ] Search box funciona (busca por nombre/doc/email)
- [ ] Paginación: 20 registros, selector 10/20/50/100
- [ ] Click lápiz → offcanvas abre en modo editar
- [ ] Click papelera → confirm + elimina
- [ ] Editar y guardar → grid se recarga
- [ ] Badge "Principal" muestra correctamente
- [ ] Tipo documento display correcto (CC, CE, PA, NIT)
- [ ] Sin errores 404 en console
- [ ] Tabulator inicializa correctamente
- [ ] Lazy-load funciona (no carga hasta click en tab)

---

## 🎨 UX Details

| Elemento | Icono | Color | Nota |
|----------|-------|-------|------|
| Tab Directorio | `bi-truck` | Primary | Default tab |
| Tab CxP | `bi-wallet2` | Primary | Info placeholder |
| Tab Representantes | `bi-person-check` | Primary | NEW v3.17.0 |
| Badge Principal | N/A | `bg-success` | Verde |
| Botón Editar | `bi-pencil` | Outline-primary | |
| Botón Eliminar | `bi-trash` | Outline-danger | |

---

## 📊 Grid Columns (Representantes Tab)

```
┌──────────┬──────────────────┬────────┬───────────────┬───────────┐
│ Documento│ Nombre Completo  │ Cargo  │Email/Teléfono │ Acciones  │
├──────────┼──────────────────┼────────┼───────────────┼───────────┤
│1234567890│ Juan Perez       │Gerente │juan@emp.com   │ ✎  🗑     │
│CE-ABC123 │ María García ✓   │Directora│maria@emp.com │ ✎  🗑     │
│ PA-XYZ789│ Carlos López     │Manager │300-1234567    │ ✎  🗑     │
└──────────┴──────────────────┴────────┴───────────────┴───────────┘
```

*✓ = Badge "Principal"*

---

## 🔗 Referencias Técnicas

- **API Endpoint**: `/api/v1/proveedores/representantes/`
- **ViewSet**: `RepresentanteViewSet` (11 ViewSets totales)
- **Serializers**: `RepresentanteListSerializer` + `RepresentanteDetailSerializer`
- **Permissions**: `IsTenantMember`, `IsTenantAdminOrReadOnly`
- **JS Modules**:
  - `representante.api.js` (SSoT para URLs)
  - `representante_list.js` (cargarTabla, renderizar)
  - `representante_editor.js` (form handle)
- **Templates**:
  - `representantes_directory.html` (grid + JS inline)
  - `offcanvas_representante_form.html` (form modal)

---

## 📝 Notas

- El grid es **consolidado**: muestra representantes de **TODOS** los proveedores
- **Lazy-load**: no consume recursos hasta que el usuario hace click
- **Search global**: busca en nombre, documento y email (no filtrado por proveedor)
- **Acciones directas**: editar y eliminar sin abrir proveedor padre
- **Bootstrap 5.3**: modal, tabs, grid responsive
- **Feature-Sliced Architecture**: partial modular, JS aislado, namespaced

---

**Status:** ✅ READY FOR TESTING  
**Last Updated:** 2026-06-10  
**Workspace Version:** v2.95 + Proveedores v3.17.0
