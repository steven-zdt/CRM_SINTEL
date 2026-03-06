# Inventario de list.html y DataTables por App

## Estado Actual

### ✅ Completado

#### 1. Facturas (Canon)
- [x] `list.html` — ✅ Actualizado con DataTables (id: `#dt-facturas-main`)
- [x] `id tabla`: `#dt-facturas-main`
- [x] `columnas`: Número, Naturaleza, Emisor, Receptor, Emisión, Subtotal, Impuestos, Total, CUFE, Acciones
- [x] `JS`: `facturas.dt.js` ✅ (DataTables server-side POST)
- [x] `endpoint`: `POST /api/v1/facturas/dt/facturas/` ✅
- [x] **Estado**: ✅ Completado

---

### 🔄 Pendiente (Apps que requieren list.html)

#### 2. Empresa
- [ ] `list.html` — NO existe (singleton, puede no requerir tabla)
- [ ] `id tabla`: `#dt-empresa-main` (si se implementa)
- [ ] `columnas`: Razón Social, NIT, Dirección, Teléfono, Email, Acciones
- [ ] `JS`: `empresa.ui.js` (renderiza directamente, NO tabla)
- [ ] `endpoint`: `/api/v1/core/empresa/` (GET, singleton)
- [ ] **Acción**: Evaluar si requiere tabla (singleton)

#### 3. Gastos
- [x] `list.html` — ✅ Creado con DataTables (id: `#dt-gastos-main`)
- [x] `id tabla`: `#dt-gastos-main`
- [x] `columnas`: Descripción, Monto, Fecha, Categoría, Acciones
- [x] `JS`: `gastos.dt.js` ✅ (DataTables server-side POST)
- [x] `endpoint`: `POST /api/v1/gastos/dt/gastos/` ✅
- [x] **Estado**: ✅ Completado

#### 4. Proveedores
- [x] `list.html` — ✅ Creado con DataTables (id: `#dt-proveedores-main`)
- [x] `id tabla`: `#dt-proveedores-main`
- [x] `columnas`: Razón Social, NIT, Dirección, Teléfono, Email, Acciones
- [x] `JS`: `proveedores.dt.js` ✅ (DataTables server-side POST)
- [x] `endpoint`: `POST /api/v1/proveedores/dt/proveedores/` ✅
- [x] **Estado**: ✅ Completado

#### 5. Empleados
- [x] `list.html` — ✅ Creado con DataTables (id: `#dt-empleados-main`)
- [x] `id tabla`: `#dt-empleados-main`
- [x] `columnas`: Nombre Completo, Documento, Email, Teléfono, Estado, Acciones
- [x] `JS`: `empleados.dt.js` ✅ (DataTables server-side POST)
- [x] `endpoint`: `POST /api/v1/empleados/dt/empleados/` ✅
- [x] **Estado**: ✅ Completado

#### 6. Contabilidad
- [ ] `list.html` — NO existe (tiene sub-módulos: cuentas, asientos)
- [ ] `id tabla`: `#dt-cuentas-main`, `#dt-asientos-main` (separados)
- [ ] `columnas Cuentas`: Código, Nombre, Tipo, Descripción, Acciones
- [ ] `columnas Asientos`: Número, Fecha, Descripción, Estado, Acciones
- [ ] `JS`: `contabilidad.ui.js` (NO existe tabla)
- [ ] `endpoint`: `/api/v1/core/contabilidad/cuentas/`, `/api/v1/core/contabilidad/asientos/` (GET, NO tienen /dt/)
- [ ] **Acción**: Crear list.html con tabs o secciones + DataTables + endpoints /dt/

#### 7. Inventario
- [ ] `list.html` — NO existe (tiene sub-módulos: catálogo, activos)
- [ ] `id tabla`: `#dt-catalogo-main`, `#dt-activos-main` (separados)
- [ ] `columnas Catálogo`: Código, Nombre, Categoría, Stock, Precio, Acciones
- [ ] `columnas Activos`: Código, Nombre, Estado, Ubicación, Acciones
- [ ] `JS`: `inventario.ui.js` (NO existe tabla)
- [ ] `endpoint`: `/api/v1/core/inventario/catalogo/`, `/api/v1/core/inventario/activos/` (GET, NO tienen /dt/)
- [ ] **Acción**: Crear list.html con tabs + DataTables + endpoints /dt/

#### 8. Perfil
- [ ] `list.html` — NO existe (no requiere tabla, es perfil individual)
- [ ] **Acción**: No requiere tabla

#### 9. Mail (MailDigester)
- [ ] `list.html` — NO existe (lista ejecuciones)
- [ ] `id tabla`: `#dt-mail-runs-main`
- [ ] `columnas`: Estado, Configuración, Fecha Inicio, Fecha Fin, Mensajes Procesados, Facturas Creadas, Acciones
- [ ] `JS`: `mail.ui.js` (NO existe tabla)
- [ ] `endpoint`: `/api/v1/core/maildigester/runs/` (GET, NO tiene /dt/)
- [ ] **Acción**: Crear list.html + DataTables + endpoint /dt/

#### 10. Dashboard
- [ ] `list.html` — NO existe (panel read-only, no requiere tabla)
- [ ] **Acción**: No requiere tabla

#### 11. Landing
- [ ] `list.html` — NO existe (panel informativo, no requiere tabla)
- [ ] **Acción**: No requiere tabla

---

## Resumen de Apps que Requieren DataTables

| App | Requiere Tabla | Sub-módulos | Prioridad |
|-----|----------------|-------------|-----------|
| **Facturas** | ✅ SÍ | - | 🔴 Alta (canon) | ✅ **COMPLETADO** |
| **Gastos** | ✅ SÍ | - | 🔴 Alta | ✅ **COMPLETADO** |
| **Proveedores** | ✅ SÍ | - | 🔴 Alta | ✅ **COMPLETADO** |
| **Empleados** | ✅ SÍ | - | 🔴 Alta | ✅ **COMPLETADO** |
| **Contabilidad** | ✅ SÍ | Cuentas, Asientos | 🟡 Media |
| **Inventario** | ✅ SÍ | Catálogo, Activos | 🟡 Media |
| **Mail** | ✅ SÍ | - | 🟡 Media |
| **Empresa** | ❌ NO | - | ⚪ Baja (singleton) |
| **Perfil** | ❌ NO | - | ⚪ Baja |
| **Dashboard** | ❌ NO | - | ⚪ Baja |
| **Landing** | ❌ NO | - | ⚪ Baja |

---

## Estructura Canónica de list.html

```html
{% load static %}
<!-- Partial: Lista de {{ app_name }} -->
<section class="card">
  <div class="card-header d-flex justify-content-between align-items-center">
    <h2 class="h5 mb-0">{{ app_name|default:"Módulo" }}</h2>
    <div class="toolbar" id="{{ app }}-toolbar">
      <!-- Botones de acción del módulo -->
    </div>
  </div>
  <div class="card-body">
    <div id="{{ app }}-list-feedback" class="alert d-none" role="status" aria-live="polite"></div>
    
    <!-- Filtros (opcional) -->
    <div id="{{ app }}-filters" class="mb-3"></div>
    
    <!-- Tabla DataTables -->
    <div class="table-responsive">
      <table id="dt-{{ app }}-main" class="table table-striped table-hover w-100 align-middle">
        <thead>
          <tr>
            <!-- Columnas según app -->
            <th>Columna 1</th>
            <th>Columna 2</th>
            <th class="text-end">Columna 3</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </div>
  </div>
</section>
```

---

## Endpoints /dt/ Requeridos

| App | Endpoint | Método | Resource |
|-----|----------|--------|----------|
| **Facturas** | `/api/v1/facturas/dt/facturas/` | POST | facturas | ✅ |
| **Gastos** | `/api/v1/gastos/dt/gastos/` | POST | gastos | ✅ |
| **Proveedores** | `/api/v1/proveedores/dt/proveedores/` | POST | proveedores | ✅ |
| **Empleados** | `/api/v1/empleados/dt/empleados/` | POST | empleados | ✅ |
| **Contabilidad** | `/api/v1/core/contabilidad/dt/cuentas/` | POST | cuentas |
| **Contabilidad** | `/api/v1/core/contabilidad/dt/asientos/` | POST | asientos |
| **Inventario** | `/api/v1/core/inventario/dt/catalogo/` | POST | catalogo |
| **Inventario** | `/api/v1/core/inventario/dt/activos/` | POST | activos |
| **Mail** | `/api/v1/core/maildigester/dt/runs/` | POST | runs |

---

**Última actualización**: 2024-12-19  
**Versión**: 1.0
