# 🔄 SINCRONIZACIÓN: Workspace v2.95 + Módulo Clientes v2.61

## 📋 ANÁLISIS DE ESTADO

### Workspace.html (líneas relevantes)

**Línea 46:** Tab de clientes
```html
<li class="nav-item"><a href="#clientes" data-tab="clientes" class="nav-link">
  <i class="bi bi-person-badge me-2"></i>Clientes
</a></li>
```

**Línea 95-98:** Sección de clientes
```html
<section id="tab-clientes" class="workspace-tab" style="display: none;">
  {% include 'tenant/core/partials/clientes/list.html' %}
</section>
```

**Línea 214:** Contenedor offcanvas para clientes (ANTIGUO NAMING)
```html
<div id="offcanvas-cliente-container"></div>  <!-- ❌ ANTIGUO -->
```

**Línea 354:** Carga de assets
```html
{% include 'tenant/core/partials/clientes/assets_clientes.html' %}
```

### list.html (Clientes)

**Líneas 113-114:** Contenedores offcanvas (NUEVO NAMING)
```html
<div id="offcanvas-container-clientes"></div>      <!-- ✅ NUEVO -->
<div id="offcanvas-container-contactos"></div>     <!-- ✅ NUEVO -->
```

### PROBLEMA IDENTIFICADO

**Inconsistencia de naming:**
- workspace.html usa: `id="offcanvas-cliente-container"` (singular)
- list.html usa: `id="offcanvas-container-clientes"` (plural, estándar)

**Impacto:**
- HTMX no encuentra el contenedor correcto
- Offcanvas no se inyecta
- Flujo CRUD se rompe

---

## 🔧 SOLUCIÓN

### Opción 1: Actualizar workspace.html (RECOMENDADO)
**Cambiar naming a estándar plural en workspace.html**

```html
<!-- ANTES -->
<div id="offcanvas-cliente-container"></div>

<!-- DESPUÉS -->
<div id="offcanvas-container-clientes"></div>
<div id="offcanvas-container-contactos"></div>
```

**Ventaja:** Alineado con patrón de otros módulos (empleados, contabilidad, etc.)

### Opción 2: Actualizar list.html
**Cambiar list.html a usar singular**

```html
<!-- ANTES -->
<div id="offcanvas-container-clientes"></div>
<div id="offcanvas-container-contactos"></div>

<!-- DESPUÉS -->
<div id="offcanvas-cliente-container"></div>
<div id="offcanvas-contacto-container"></div>
```

**Desventaja:** Inconsistente con otros módulos

---

## ✅ IMPLEMENTACIÓN: Opción 1 (ELEGIDA)

### Paso 1: Actualizar workspace.html

**Cambio en línea 214:**
```html
<!-- ❌ ANTES -->
<div id="offcanvas-cliente-container"></div>

<!-- ✅ DESPUÉS -->
<div id="offcanvas-container-clientes"></div>
<div id="offcanvas-container-contactos"></div>
```

### Paso 2: Verificar assets_clientes.html

**Estado actual:** ✅ CORRECTO
```html
<div id="offcanvas-container-clientes"></div>      ✅
<div id="offcanvas-container-contactos"></div>     ✅
```

No requiere cambios.

### Paso 3: Verificar list.html

**Estado actual:** ✅ CORRECTO
```html
<div id="offcanvas-container-clientes"></div>      ✅
<div id="offcanvas-container-contactos"></div>     ✅
```

No requiere cambios (estos contenedores son internos del tab, opcionales).

---

## 🔗 FLUJO DE INTEGRACIÓN

### Inicio de Carga

```
1. workspace.html carga
   ├─ Sidebar: Tab "Clientes"
   ├─ Section: #tab-clientes
   │  └─ Include: list.html
   │     ├─ Estructura HTML con Alpine.js
   │     ├─ Contenedores internos (opcional)
   │     └─ Inline Alpine.js module (clientesListModule)
   │
   └─ Global Offcanvas Containers (workspace.html)
      ├─ #offcanvas-container-clientes  ← HTMX inyecta aquí
      └─ #offcanvas-container-contactos ← HTMX inyecta aquí

2. assets_clientes.html carga
   ├─ clientes.api.js
   ├─ contactos.api.js
   ├─ clientes.list.js (fallback)
   ├─ clientes.editor.js
   ├─ clientes.contactos.js
   └─ HTMX event delegation script
```

### Cuando usuario abre Tab Clientes

```
1. Bootstrap Tab activation
   └─ Dispara event 'shown.bs.tab'

2. Alpine.js escucha evento
   └─ @shown.bs.tab="handleTabChange($event)"

3. handleTabChange() detecta tab-clientes
   └─ Llama: loadClientesTable()

4. loadClientesTable()
   ├─ TabulatorFactory.create('#grid-clientes', '/api/v1/clientes/', ...)
   ├─ Setea: clientesLoaded = true
   │  └─ Spinner desaparece
   │  └─ Grid aparece
   └─ Tabla se renderiza con datos

5. [Background] GET /api/v1/clientes/ completa
   └─ Datos se cargan en tabla sin spinner visible
```

### Cuando usuario hace click "Editar" en tabla

```
1. Tabla Tabulator cellClick handler
   └─ Llama: this.editarCliente(id)

2. editarCliente(id)
   └─ HTMX: GET /api/v1/clientes/{id}/render-offcanvas/editar/

3. Backend retorna offcanvas_editar_cliente.html
   └─ HTMX inyecta en #offcanvas-container-clientes
   └─ Template script dispara bootstrap.Offcanvas.show()

4. Offcanvas se abre
   └─ Dispara 'shown.bs.offcanvas'

5. clientes.editor.js escucha evento
   └─ @shown.bs.offcanvas → initFormulario()

6. initFormulario()
   ├─ Attacha listeners a form
   ├─ Attacha listeners a botones
   └─ form#form-cliente AHORA EXISTE EN DOM ✅

7. Usuario edita y guarda
   └─ guardarCliente() → PATCH /api/v1/clientes/{id}/

8. Success → Dispara 'clienteGuardado'
   └─ Alpine.js @clienteGuardado → reloadClientesTable()
   └─ Tabla se actualiza automáticamente
```

---

## 📐 ESTRUCTURA FINAL ALINEADA

```
workspace.html (Principal)
│
├─ Sidebar (Nav)
│  └─ Link: #clientes
│
├─ Content Area
│  └─ Tab: #tab-clientes (style="display: none;" inicialmente)
│     └─ Include: list.html
│        ├─ Card con Alpine.js (clientesListModule)
│        │  ├─ x-data="clientesListModule()"
│        │  ├─ @shown.bs.tab="handleTabChange($event)"
│        │  ├─ @clienteGuardado="reloadClientesTable()"
│        │  ├─ @contactoGuardado="reloadContactosTable()"
│        │  ├─ @contactoEliminado="reloadContactosTable()"
│        │  │
│        │  ├─ Tab 1: Clientes
│        │  │  ├─ Search
│        │  │  ├─ Botón "Nuevo Cliente"
│        │  │  ├─ Spinner (x-show="!clientesLoaded && loadingClientes")
│        │  │  ├─ Grid (x-show="clientesLoaded")
│        │  │  └─ Empty State (x-show="!loadingClientes && clientesLoaded && clientesCount === 0")
│        │  │
│        │  ├─ Tab 2: Contactos
│        │  │  ├─ Search
│        │  │  ├─ Botón "Nuevo Contacto"
│        │  │  ├─ Spinner (x-show="!contactosLoaded && loadingContactos")
│        │  │  ├─ Grid (x-show="contactosLoaded")
│        │  │  └─ Empty State
│        │  │
│        │  ├─ Inline: clientesListModule() Alpine.js
│        │  │  ├─ loadingClientes / clientesLoaded / clientesCount
│        │  │  ├─ loadingContactos / contactosLoaded / contactosCount
│        │  │  ├─ loadClientesTable() / reloadClientesTable()
│        │  │  ├─ loadContactosTable() / reloadContactosTable()
│        │  │  ├─ editarCliente() / eliminarCliente()
│        │  │  ├─ editarContacto() / eliminarContacto()
│        │  │  ├─ getClientesColumns()
│        │  │  └─ getContactosColumns()
│        │  │
│        │  └─ Contenedores internos (opcionales)
│        │     ├─ #offcanvas-container-clientes
│        │     └─ #offcanvas-container-contactos
│        │
│        └─ Script: Inline clientesListModule()
│
├─ Global Offcanvas Containers
│  ├─ #offcanvas-container-clientes  ← HTMX inyecta offcanvas_editar_cliente.html
│  ├─ #offcanvas-container-contactos ← HTMX inyecta contactos_offcanvas.html
│  └─ ... (otros módulos)
│
└─ Scripts (assets)
   ├─ assets_core.html (TabulatorFactory, http(), UIManager, etc.)
   │
   └─ assets_clientes.html
      ├─ clientes.api.js
      ├─ contactos.api.js
      ├─ clientes.list.js (fallback si Alpine.js falla)
      ├─ clientes.editor.js (event-based form init)
      ├─ clientes.contactos.js (event-based form init)
      └─ HTMX event delegation
```

---

## ⚙️ SYNCHRONIZATION CHECKLIST

### workspace.html

- [x] Línea 46: Tab de clientes correcto
- [x] Línea 95: Sección de clientes con list.html
- [ ] Línea 214: **ACTUALIZAR** `offcanvas-cliente-container` → `offcanvas-container-clientes` + `offcanvas-container-contactos`
- [x] Línea 354: assets_clientes.html cargado

### list.html

- [x] Alpine.js x-data correcta
- [x] @shown.bs.tab binding
- [x] Contenedores offcanvas (internos)
- [x] Inline clientesListModule()
- [x] Spinner visibility logic (fixed en commit 5cc26fb)
- [x] Grid visibility logic (fixed en commit 5cc26fb)

### assets_clientes.html

- [x] API wrappers (clientes.api.js, contactos.api.js)
- [x] Feature modules (list, editor, detalle, contactos)
- [x] HTMX event delegation

### clientes.editor.js

- [x] Event-based initialization (shown.bs.offcanvas)
- [x] Form ID unification (#form-cliente)
- [x] Offcanvas ID unification (#offcanvas-cliente)

### clientes.contactos.js

- [x] Event-based initialization (shown.bs.offcanvas)
- [x] Form submission
- [x] Error handling

---

## 🚀 CAMBIOS NECESARIOS

### CRÍTICO: Actualizar workspace.html

**Línea 214 - ANTES:**
```html
<div id="offcanvas-cliente-container"></div>
```

**Línea 214 - DESPUÉS:**
```html
{# ⚠️ v2.61: Módulo Clientes - Contenedores Offcanvas globales #}
<div id="offcanvas-container-clientes"></div>
<div id="offcanvas-container-contactos"></div>
```

---

## 📊 ESTADO FINAL

Una vez aplicados estos cambios, la alineación será:

| Componente | Ubicación | ID Container | Estado |
|---|---|---|---|
| Clientes Tab | workspace.html:95 | #tab-clientes | ✅ OK |
| Clientes Section | list.html | Alpine.js module | ✅ OK |
| Clientes Offcanvas | workspace.html | #offcanvas-container-clientes | 🔴 REQUIERE UPDATE |
| Contactos Offcanvas | workspace.html | #offcanvas-container-contactos | ➕ REQUIERE AGREGAR |
| Assets Clientes | assets_clientes.html | (scripts) | ✅ OK |

---

## 📝 COMMIT NECESARIO

Cambio simple en workspace.html:

```
git commit -m "sync: align offcanvas container IDs with Clientes v2.61 module

ISSUE: workspace.html used id=\"offcanvas-cliente-container\" (singular)
       but list.html expected id=\"offcanvas-container-clientes\" (plural)

FIX: Update workspace.html to use standard naming convention
     - offcanvas-cliente-container → offcanvas-container-clientes
     - Add: offcanvas-container-contactos

This aligns with naming pattern used by other modules (empleados, contabilidad)
and matches the IDs targeted by HTMX calls in list.html and Alpine.js module

AFFECTED: 
- offcanvas-container-clientes: receives offcanvas_editar_cliente.html
- offcanvas-container-contactos: receives contactos_offcanvas.html"
```

---

**Estado actual:** 🔴 REQUIERE SINCRONIZACIÓN
**Cambios necesarios:** 1 archivo (workspace.html, línea 214)
**Impacto:** CRÍTICO - Sin esta actualización, los offcanvas no se inyectan correctamente
