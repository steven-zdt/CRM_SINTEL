# Checklist de Modales por App

## Estado de Implementación

### ✅ Completado

#### 1. Facturas (Canon)
- [x] `modals.html` — Modal de importar (parse-only)
- [x] `facturas.modals.js` — Lógica completa de modales
- [x] Modales dinámicos: detalle, XML
- [x] Confirmación de eliminación
- [x] Flujo parse-only: preview + persistencia desde DTO
- [x] Endpoints universales: `/api/v1/core/documentos/upload/`, `/api/v1/core/documentos/{id}/xml/`, `/api/v1/core/documentos/{id}/`
- [x] Endpoint app: `/api/v1/facturas/create-from-dto/`
- [x] `assets_facturas.html` incluye `facturas.modals.js`

#### 2. Empresa
- [x] `modals.html` — Modales CRUD (create, edit, detail)
- [x] `empresa.modals.js` — Lógica completa de modales
- [x] Modales estáticos: crear, editar, detalle
- [x] Confirmación de eliminación (nativo `confirm()`)
- [x] Endpoints: `/api/v1/core/empresa/`, `/api/v1/empresas/`
- [x] `assets_empresas.html` incluye `empresa.modals.js`

#### 3. Gastos
- [x] `modals.html` — Modales CRUD + Import (parse-only)
- [x] `gastos.modals.js` — Lógica completa de modales
- [x] Modales estáticos: crear, editar, detalle, importar
- [x] Confirmación de eliminación
- [x] Flujo parse-only: preview + persistencia desde DTO
- [x] Endpoints universales: `/api/v1/core/documentos/upload/?tipo=gasto`
- [x] Endpoint app: `/api/v1/gastos/create-from-dto/`
- [x] `assets_gastos.html` incluye `gastos.modals.js`

---

### 🔄 Pendiente

#### 4. Inventario
- [ ] `modals.html` — Modales CRUD + Import (parse-only, opcional)
- [ ] `inventario.modals.js` — Lógica de modales
- [ ] Nota: Inventario tiene sub-módulos (catálogo, activos), puede requerir modales específicos
- [ ] Endpoints: `/api/v1/core/inventario/`, `/api/v1/core/documentos/upload/?tipo=inventario` (opcional)
- [ ] `assets_inventario.html` — Actualizar para incluir `inventario.modals.js`
- **Nota**: Inventario tiene estructura compleja con sub-módulos. Los modales pueden implementarse cuando se defina la estructura específica de cada sub-módulo.

#### 5. Proveedores
- [x] `modals.html` — Modales CRUD (create, edit, detail, delete)
- [x] `proveedores.modals.js` — Lógica de modales
- [x] Endpoints: `/api/v1/proveedores/`
- [x] `assets_proveedores.html` — Actualizar para incluir `proveedores.modals.js`

#### 6. Empleados
- [x] `modals.html` — Modales CRUD (create, edit, detail, delete)
- [x] `empleados.modals.js` — Lógica de modales
- [x] Nota: Empleados puede tener sub-módulos (contratos, nómina) - modales básicos implementados
- [x] Endpoints: `/api/v1/empleados/`
- [x] `assets_empleados.html` — Actualizar para incluir `empleados.modals.js`

#### 7. Contabilidad
- [x] `modals.html` — Modales CRUD (create, edit, detail, delete) para Cuentas y Asientos
- [x] `contabilidad.modals.js` — Lógica de modales (cuentas y asientos)
- [x] Nota: Contabilidad tiene sub-módulos (cuentas, asientos) - ambos implementados
- [x] Endpoints: `/api/v1/core/contabilidad/cuentas/`, `/api/v1/core/contabilidad/asientos/`
- [x] `assets_contabilidad.html` — Actualizar para incluir `contabilidad.modals.js`

#### 8. Perfil
- [x] `modals.html` — Modal de editar (solo edit, no create/delete)
- [x] `perfil.modals.js` — Lógica de modales
- [x] Endpoints: `/api/v1/core/mi-perfil/` (PATCH)
- [x] `assets_perfil.html` — Actualizar para incluir `perfil.modals.js`

#### 9. Mail (MailDigester)
- [x] `modals.html` — Modales especiales (run, stop, details)
- [x] `mail.modals.js` — Lógica de modales
- [x] Modales: `#modal-mail-run-confirm`, `#modal-mail-stop-confirm`, `#modal-mail-details`
- [x] Endpoints: `/api/v1/core/maildigester/run/`, `/api/v1/core/maildigester/run/{id}/stop/`, `/api/v1/core/maildigester/run/{id}/details/`
- [x] `assets_mail.html` — Actualizar para incluir `mail.modals.js`

#### 10. Dashboard
- [ ] No requiere modales CRUD (panel read-only)
- [ ] Verificar si necesita modales de configuración o filtros avanzados

#### 11. Landing
- [ ] No requiere modales CRUD (panel informativo)
- [ ] Verificar si necesita modales de información adicional

---

## Patrón Canónico Aplicado

### IDs de Modales
- `#modal-<app>-create` — Crear
- `#modal-<app>-edit` — Editar
- `#modal-<app>-detail` — Detalle (read-only)
- `#modal-<app>-import` — Importar (parse-only, donde aplique)
- `#modal-<app>-xml` — Ver XML (donde aplique)

### Funciones Exportadas (`window.<app>Modals`)
- `showCreateModal()` — Abre modal de crear
- `showEditModal(id)` — Abre modal de editar
- `showDetailModal(id)` — Abre modal de detalle
- `showImportModal()` — Abre modal de importar (donde aplique)
- `confirmDelete<App>(id, onSuccess, onError)` — Confirma y elimina
- `handleImport(file, preview, onSuccess, onError)` — Maneja importación (donde aplique)
- `handleConfirm(kind)` — Maneja confirmación de create/edit

### Errores Canónicos
- **409**: "Documento duplicado (409)."
- **422**: "Datos inválidos (422). Verifique los campos."
- **415**: "Formato no soportado (415)."
- **400**: "Error de parsing/detección (400)."
- **401/403**: "No tienes permisos para realizar esta acción."
- **Fallback**: `data?.detail || data?.message || "Error HTTP ${status}"`

### Orden de Scripts en `assets_<app>.html`
1. `lib/http.js`
2. `<app>.api.js`
3. `<app>.ui.js` (o `<app>.components.js` si existe)
4. `<app>.table.js` (si aplica)
5. **`<app>.modals.js`** ← NUEVO
6. `<app>.page.js`

---

## Notas de Implementación

### Apps con Parse-Only (Import)
- **Facturas**: XML UBL → DTO → persistencia
- **Gastos**: CSV/XLS/XLSX/TXT/PDF → DTO → persistencia
- **Inventario**: CSV/XLS/XLSX/TXT/PDF → DTO → persistencia (opcional)

### Apps con Modales Especiales
- **MailDigester**: Modales de ejecución (run, stop, details), no CRUD estándar
- **Perfil**: Solo edición (no create/delete)
- **Dashboard/Landing**: No requieren modales CRUD

### Apps con Sub-módulos
- **Inventario**: Catálogo, Activos (pueden requerir modales específicos)
- **Empleados**: Contratos, Nómina (pueden requerir modales específicos)
- **Contabilidad**: Cuentas, Asientos (pueden requerir modales específicos)

---

**Última actualización**: 2024-12-19  
**Versión**: 1.0
