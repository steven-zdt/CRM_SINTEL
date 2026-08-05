# Plan de Implementación: Separación de Módulos en #empleados
## Feature-Sliced CRUD Independiente — Empleados, Contratos, Nómina

**Versión Objetivo:** 3.8.0
**Estado:** PENDIENTE DE IMPLEMENTACIÓN
**Fecha:** 2026-05-21
**Alcance:** `apps/tenant/empleados/` (frontend + docs, backend sin cambios)

---

## 1. Contexto y Diagnóstico

### Estado actual (v3.7.4)

La workspace `#empleados` en `home.sintel.net.co` ya tiene 3 tabs (Empleados / Contratos / Nóminas), **pero**:

| Módulo | Estado Tab | CRUD | Problema |
|--------|-----------|------|----------|
| Empleados | Activo | Completo | Funciona bien |
| Contratos | Existente | Parcial | Solo se crea/edita desde el botón en la fila de Empleado. **Sin lista propia independiente**. `ContratoList.init()` comentado en `empleados.module.js` |
| Nómina/Devengos | Activo | Parcial | Tiene lista propia (`NominaList`), pero crear nómina solo se hace desde la fila de Empleado (botón "Registrar Nómina"). **Sin botón "Nueva Nómina" independiente** |

### Objetivo (v3.8.0)

Cada tab debe ser un módulo CRUD **completamente autónomo**:

```
Tab Empleados  → Lista + Crear + Editar + Eliminar Empleado
Tab Contratos  → Lista propia + Crear Contrato (con selector de Empleado) + Editar + Ver Detalle
Tab Nómina     → Lista propia + Crear Nómina (con selector de Empleado+Contrato) + Anular
```

> **RESTRICCIÓN CRÍTICA**: El backend (ViewSets, Serializers, Services) NO se modifica. El trabajo es 100% frontend.

---

## 2. Análisis de Brechas

### Brecha 1: `contrato_list.js` — NO EXISTE
- El orquestador llama a `w.Sintel.Empleados.ContratoList.init(gridId)` pero está **comentado** porque el módulo no existe.
- Se necesita crear `static/empleados/js/features/contrato_list.js` con tabla Tabulator consumiendo `/api/v1/empleados/contratos/`.

### Brecha 2: Contratos sin "Nuevo Contrato" independiente
- El tab Contratos no tiene botón "Nuevo Contrato".
- Crear Contrato requiere seleccionar un Empleado → el offcanvas debe incluir un selector de Empleado (FK).
- El endpoint `render-offcanvas/crear/` acepta `?empleado=<id>` como query param.
- Solución: Botón "Nuevo Contrato" → offcanvas con buscador de empleado → `GET /api/v1/empleados/contratos/render-offcanvas/crear/?empleado={id}`.

### Brecha 3: Nómina sin "Nueva Nómina" independiente
- El tab Nóminas no tiene botón "Registrar Nómina".
- Crear Nómina requiere Empleado + Contrato ACTIVO → selector en offcanvas.
- El endpoint `render-offcanvas/crear/` acepta `?empleado=<id>` como query param.
- Solución: Botón "Nueva Nómina" → offcanvas con buscador de empleado → carga contrato automáticamente.

### Brecha 4: Template monolítico sin botones de acción en tabs de Contratos y Nóminas
- El `empleados_list.html` tiene los 3 tabs pero Contratos y Nóminas carecen de botón de creación.

---

## 3. Archivos a Crear / Modificar

### Archivos NUEVOS

| Archivo | Descripción |
|---------|-------------|
| `features/contrato_list.js` | Tabla Tabulator de Contratos independiente con CRUD |

### Archivos a MODIFICAR

| Archivo | Cambio |
|---------|--------|
| `templates/tenant/empleados/empleados_list.html` | Agregar botón "Nuevo Contrato" en Tab 2 y botón "Nueva Nómina" en Tab 3 |
| `static/empleados/js/empleados.module.js` | Descomentar `ContratoList.init()` y conectar el nuevo módulo |
| `templates/tenant/empleados/assets_empleados.html` | Agregar `<script>` para `contrato_list.js` |

---

## 4. Especificación de `contrato_list.js`

### Namespace
```javascript
window.Sintel.Empleados.ContratoList
```

### Columnas Tabulator

| Campo | Título | Ancho | Formato |
|-------|--------|-------|---------|
| `empleado_nombre` | Empleado | min 160 | texto |
| `tipo` | Tipo | 130 | badge (FIJO=blue, INDEF=green, OBRA=yellow, PRESTACION=gray) |
| `fecha_inicio` | Inicio | 100 | fecha |
| `fecha_fin` | Fin | 100 | fecha o "Indefinido" |
| `salario_mensual` | Salario | 130 | COP formatter |
| `estado` | Estado | 100 | badge (ACTIVO=green, INACTIVO=red, HISTORICO=gray) |
| Acciones | Acciones | 180 | Ver Detalle / Editar / Cancelar |

### Endpoint
- Lista: `GET /api/v1/empleados/contratos/`
- Crear: `GET /api/v1/empleados/contratos/render-offcanvas/crear/?empleado={id}`
- Editar: `GET /api/v1/empleados/contratos/{uuid}/render-offcanvas/editar/`
- Detalle: `GET /api/v1/empleados/contratos/{uuid}/render-offcanvas/detalle/`

### Acciones de Celda
```javascript
switch (action) {
    case 'ver-detalle':   ContratoEditor.openDetail(uuid); break;
    case 'editar':        ContratoEditor.open(null, uuid); break;
    case 'cancelar':      cancelarContrato(uuid); break;
}
```

---

## 5. Cambios en Template `empleados_list.html`

### Tab 2 (Contratos) — Agregar toolbar con botón

```html
{# TAB 2: CONTRATOS - Agregar después del input de búsqueda #}
<button class="btn btn-primary btn-sm" id="btn-nuevo-contrato">
  <i class="bi bi-plus-lg me-1"></i>Nuevo Contrato
</button>
```

El botón abrirá un offcanvas de selección de empleado antes de redirigir al formulario de creación. El `ContratoEditor.open(empleadoId)` ya soporta esto.

### Tab 3 (Nóminas) — Agregar toolbar con botón

```html
{# TAB 3: NOMINAS - Agregar después del input de búsqueda #}
<button class="btn btn-primary btn-sm" id="btn-nueva-nomina">
  <i class="bi bi-cash-coin me-1"></i>Registrar Nómina
</button>
```

El botón abrirá el `DevengoEditor` con selección de empleado libre (no desde fila).

---

## 6. Cambios en `empleados.module.js`

```javascript
} else if (tabName === 'contratos' && w.Sintel.Empleados.ContratoList) {
    // DESCOMENTAR:
    await w.Sintel.Empleados.ContratoList.init(gridId);
}
```

Además, conectar los botones "Nuevo Contrato" y "Nueva Nómina":

```javascript
// En init():
const btnNuevoContrato = d.getElementById('btn-nuevo-contrato');
if (btnNuevoContrato) {
    btnNuevoContrato.addEventListener('click', () => {
        // Abrir selector de empleado primero
        // (puede ser un offcanvas simple de búsqueda o el gestor-offcanvas)
        w.Sintel.Empleados.ContratoEditor.open(null, null); // sin args = selector
    });
}

const btnNuevaNomina = d.getElementById('btn-nueva-nomina');
if (btnNuevaNomina) {
    btnNuevaNomina.addEventListener('click', () => {
        w.Sintel.Empleados.DevengoEditor?.open(null); // null = sin empleado preseleccionado
    });
}
```

---

## 7. Orden de Implementación (Microtareas)

### Fase 1 — Contrato List (prioridad alta)
1. Crear `features/contrato_list.js`
2. Registrar en `assets_empleados.html`
3. Descomentar `ContratoList.init()` en `empleados.module.js`
4. Agregar botón "Nuevo Contrato" en `empleados_list.html`

### Fase 2 — Nómina Crear independiente (prioridad media)
1. Agregar botón "Nueva Nómina" en `empleados_list.html`
2. Revisar `devengo_editor.js` para soporte sin `empleadoId` preseleccionado
3. Si el editor no soporta null, agregar selector de empleado al offcanvas de creación

### Fase 3 — Validación y Documentación
1. Smoke test del flujo: Tab Contratos → Nueva Contrato → Tabla actualizada
2. Smoke test del flujo: Tab Nómina → Nueva Nómina → Tabla actualizada
3. Actualizar `AUDITORIA_FLUJO_EMPLEADOS.md` con nueva estructura

---

## 8. Reglas de Aislamiento (FSD Compliance)

Cada módulo/tab debe respetar:

- **Sin referencias cruzadas de DOM**: el Tab Contratos no puede buscar IDs del Tab Empleados.
- **Reload aislado**: `ContratoList.reload()` recarga solo la tabla de contratos.
- **Namespace propio**: `window.Sintel.Empleados.ContratoList` separado de `window.Sintel.Empleados.EmpleadoList`.
- **Conexión permitida**: Un módulo PUEDE llamar al editor de otro (ej: desde EmpleadoList se llama a `ContratoEditor.open()`), pero la tabla de cada módulo es independiente.

---

## 9. Diagrama de Dependencias (Post-Implementación)

```
empleados.module.js (Orquestador)
  ├── tab:empleados  → EmpleadoList.init()  → EmpleadoEditor / ContratoEditor (cross-call OK)
  ├── tab:contratos  → ContratoList.init()  → ContratoEditor (CRUD propio)
  └── tab:nominas    → NominaList.init()    → DevengoEditor (CRUD propio)

empleados.api.js (SSoT URLs) ← usado por todos los módulos
```

---

## 10. Criterios de Aceptación

- [x] Tab Contratos muestra tabla con datos de `/api/v1/empleados/contratos/`
- [x] Botón "Nuevo Contrato" abre offcanvas de creación funcional
- [x] Botón "Editar" en fila abre offcanvas de edición funcional
- [x] Botón "Ver Detalle" en fila abre offcanvas de detalle
- [x] Tab Nóminas tiene botón "Registrar Nómina" independiente
- [x] Cada tabla se recarga de forma independiente sin afectar las otras
- [x] La lógica secuencial (Empleado → Contrato → Devengo) sigue siendo válida en backend
