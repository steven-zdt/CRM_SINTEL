# Testing Checklist: Representante v3.17.0 Sincronización Workspace

**Fecha:** 2026-06-10  
**Versión:** v3.17.0  
**Estado:** SYNCHRONIZATION COMPLETE

---

## 🔧 Pre-Testing Setup

- [ ] Aplicar migración: `docker compose exec web python manage.py migrate tenant_proveedores 0018`
- [ ] Verificar tablas creadas en BD:
  - [ ] `tenant_proveedores_representante` existe
  - [ ] Constraint `uniq_representante_empresa_proveedor_doc` presente
  - [ ] Índices creados correctamente
- [ ] Acceder a workspace: `http://localhost:8000/workspace/#proveedores`

---

## ✅ FASE 1: Backend API

### Endpoints Básicos
- [ ] **GET** `/api/v1/proveedores/representantes/?proveedor_uuid={uuid}`
  - Respuesta 200 con array vacío `[]` (inicial)
  - Headers contienen `Content-Type: application/json`
- [ ] **POST** `/api/v1/proveedores/representantes/`
  - Cuerpo: `{ tipo_documento: "CC", numero_documento: "1234567890", nombre_completo: "Juan Perez", cargo: "Gerente", es_principal: true, email_contacto: "juan@ejemplo.com" }`
  - Respuesta 201 Created con UUID generado
- [ ] **PATCH** `/api/v1/proveedores/representantes/{uuid}/`
  - Actualizar `cargo` o `es_principal`
  - Respuesta 200 OK
- [ ] **DELETE** `/api/v1/proveedores/representantes/{uuid}/`
  - Respuesta 204 No Content

### DSV Validation (Double Semantic Verification)
- [ ] Crear representante con `proveedor_uuid` incorrecto → `ValidationError` 400
- [ ] Crear representante con documento duplicado → `ValidationError` 400 (Constraint violation)
- [ ] Eliminar único representante principal → `ValidationError` 400 ("No se puede eliminar...")

---

## ✅ FASE 2: Workspace UI — Lista Proveedores

### Grid Principal (`#grid-proveedores`)
- [ ] Tabla carga correctamente en workspace/#proveedores
- [ ] 5 columnas visibles: ID | NIT/Documento | Razón Social | CxP | Estado | Acciones
- [ ] Search funciona (busca en NIT y Razón Social)
- [ ] Botones acciones:
  - [ ] Lápiz (Editar) abre offcanvas crear/editar
  - [ ] Papelera (Eliminar) deshabilitada si Activo=True

### Row Click (Detalle Proveedor)
- [ ] Hacer click en fila abre offcanvas en **modo detalle** (read-only)
- [ ] Offcanvas muestra **3 tabs**:
  1. **Información** (predeterminado)
  2. **Facturas de Compra** (lazy load)
  3. **Representantes** (lazy load) ⭐

---

## ✅ FASE 3: Offcanvas Detalle — Tab Representantes

### Tab Visual
- [ ] Tab "Representantes" aparece en nav-tabs con icono `bi-person-check`
- [ ] Click en tab no causa error 404

### Tabla de Representantes
- [ ] Tabla carga (vacía inicialmente)
- [ ] Empty state mostrado: "No hay representantes registrados aún"
- [ ] Botón "+ Agregar Representante" visible en header

### Lazy Load
- [ ] Primer click en tab carga tabla vacía
- [ ] Tabla **no** se carga al abrir offcanvas (lazy: solo al activar tab)
- [ ] Console debe mostrar:
  ```
  [representante_list.js] Cargando representantes para proveedor {uuid}
  ```

---

## ✅ FASE 4: Offcanvas Form — Crear/Editar Representante

### Abrir Form (Nuevo)
- [ ] Click "+ Agregar Representante" abre `#offcanvas-representante`
- [ ] Título en offcanvas: "Nuevo Representante"
- [ ] Todos los campos vacíos
- [ ] Checkbox `es_principal` unchecked

### Abrir Form (Editar)
- [ ] Click lápiz en fila de tabla abre offcanvas
- [ ] Título: "Editar Representante"
- [ ] Campos precargados con valores actuales
- [ ] Checkbox `es_principal` refleja estado actual

### Validación Campos
- [ ] **Tipo Documento** — required, select dropdown
  - [ ] Opciones: CC, CE, PA, NIT
- [ ] **Número Documento** — required, text input
- [ ] **Nombre Completo** — required, text input
- [ ] **Email** — optional, email validation
  - [ ] Submit con email inválido → HTML5 validation error
- [ ] **Teléfono** — optional, text input
- [ ] **Cargo** — required, defaults to "Representante Legal"
- [ ] **es_principal** — checkbox optional

### Form Submit
- [ ] Submit sin llenar required → HTML5 validation error (campo resaltado)
- [ ] Submit con datos válidos → Llamada PATCH/POST a API
  - [ ] Console muestra: `[representante_editor.js] Guardando representante...`
  - [ ] Respuesta 200/201 → Success notification: "Representante creado/actualizado correctamente"
  - [ ] Offcanvas cierra
  - [ ] Tabla de representantes se recarga automáticamente
  - [ ] Nueva fila aparece en tabla

### Error Handling
- [ ] Email duplicado → Error 400 + notificación roja
- [ ] Documento duplicado → Error 400 + notificación roja
- [ ] Red error → Error 500 + notificación roja

---

## ✅ FASE 5: Tabla Representantes — Acciones

### Tabla Columns (cuando cargada)
- [ ] Documento: muestra número + tipo_documento_display en secondary text
- [ ] Nombre: muestra nombre_completo + badge "Principal" si es_principal=true
- [ ] Cargo: muestra cargo
- [ ] Contacto: muestra email o teléfono
- [ ] Acciones: botones editar/eliminar

### Editar desde Tabla
- [ ] Click lápiz en fila → offcanvas abre en modo editar
- [ ] Campos precargados correctamente
- [ ] Cambiar cargo + guardar → tabla se actualiza

### Eliminar desde Tabla
- [ ] Click papelera → confirm dialog: "¿Está seguro de eliminar este representante?"
- [ ] Cancel → offcanvas permanece abierto
- [ ] OK → API delete llamada
  - [ ] Respuesta 204 → Success notification
  - [ ] Fila se elimina de tabla
  - [ ] Offcanvas permanece abierto

### Eliminar Principal — Guard
- [ ] Crear 1 representante con es_principal=true
- [ ] Click eliminar → Debe mostrar error:
  ```
  "No se puede eliminar el único representante principal.
   Asigne primero otro representante como principal."
  ```
- [ ] Crear 2do representante
- [ ] Cambiar 1er representante es_principal=false
- [ ] Ahora sí se puede eliminar el 1er representante

---

## ✅ FASE 6: Sincronización Frontend

### Assets Cargados
- [ ] Abrir DevTools → Network → buscar:
  - [ ] ✅ `representante.api.js` (loaded)
  - [ ] ✅ `representante_list.js` (loaded)
  - [ ] ✅ `representante_editor.js` (loaded)
- [ ] Console NO muestra errores 404 en scripts

### Namespaces Global
- [ ] Ejecutar en console:
  ```javascript
  window.Sintel.Representante.listar('{uuid}')
  // Debe retornar Promise que resuelve a array
  ```
- [ ] Ejecutar:
  ```javascript
  window.Sintel.Proveedores.Representante.cargarTabla('{uuid}')
  // Debe renderizar tabla en #tabla-representantes
  ```
- [ ] Ejecutar:
  ```javascript
  window.Sintel.Proveedores.abrirFormRepresentante(null, '{uuid}')
  // Debe abrir offcanvas vacío
  ```

### Event Listeners
- [ ] Abrir offcanvas detalle → tab-representantes-btn tiene listener `shown.bs.tab`
- [ ] Click en tab → listener dispara → `cargarTabla()` ejecuta
- [ ] Click "+ Agregar" → listener dispara → form abre sin errores

---

## ✅ FASE 7: Integration Tests

### Flujo Completo (Happy Path)
1. [ ] Navegarpara a workspace/#proveedores
2. [ ] Hacer click en fila de proveedor (row click)
3. [ ] Offcanvas abre en modo detalle
4. [ ] Click tab "Representantes"
5. [ ] Tabla carga (vacía)
6. [ ] Click "+ Agregar Representante"
7. [ ] Formulario abre
8. [ ] Llenar: CC, 12345678, Juan Perez, cargo, email@ejemplo.com, checkbox ✓
9. [ ] Click "Guardar"
10. [ ] Notificación success
11. [ ] Offcanvas cierra
12. [ ] Tabla se actualiza, nueva fila visible
13. [ ] Nueva fila muestra:
    - Documento: "12345678" + "Cedula de Ciudadania"
    - Nombre: "Juan Perez" + badge "Principal"
    - Cargo: "cargo"
    - Contacto: "email@ejemplo.com"

### Multi-Representante
1. [ ] Crear 2do representante (Sin checkbox principal)
2. [ ] Tabla muestra 2 filas
3. [ ] 1er: badge Principal
4. [ ] 2do: sin badge
5. [ ] Editar 2do: marcar checkbox principal
6. [ ] Guardar
7. [ ] Tabla se actualiza: badge "Principal" cambia a 2do

### Cross-Tenant Isolation (DSV)
- [ ] Log out / switch a otro tenant
- [ ] Abrir workspace/#proveedores de otro tenant
- [ ] Representantes creados en tenant A NO aparecen en tenant B ✓

---

## 🚨 Critical Issues to Catch

| Issue | Test | Expected |
|-------|------|----------|
| Script 404 | DevTools Network | Todos los .js archivos status 200 |
| JSON parse error | Console | Sin errores tipo "Cannot read property..." |
| Backend 404 | API call | Respuesta 404 si endpoint no registrado |
| CSRF 403 | POST/PATCH/DELETE | Requiere CSRF token, no error 403 genérico |
| Table not rendering | Open tab | Tabla HTML visible, no error en console |
| Form not opening | Click button | Offcanvas aparece sin 500 error |
| Lazy load not firing | Open tab | `shown.bs.tab` listener activa función |

---

## 📝 Notes

- **Cache:** Si cambios en JS no se reflejan, limpiar browser cache (Ctrl+Shift+Delete)
- **Console Logs:** Buscar `[representante_*]` para debug
- **Network Throttling:** Probar con "Slow 3G" en DevTools para simular lag

---

**Sync Status:** ✅ COMPLETE v3.17.0  
**Last Updated:** 2026-06-10  
**Tester:** User  
**Result:** PASS / FAIL
