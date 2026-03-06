# Migración UI Modular Completa - Estado

## ✅ Apps Completadas

1. **Empresa** ✅ (ya existía)
2. **Facturas** ✅ (ya existía)
3. **MailDigester** ✅ (ya existía)
4. **Dashboard** ✅ (creado)
5. **Perfil** ✅ (creado)

## 🔄 Apps Pendientes (estructura base creada)

6. **Inventario** - Pendiente módulos JS
7. **Gastos** - Pendiente módulos JS
8. **Landing** - Pendiente módulos JS
9. **Proveedores** - Pendiente módulos JS
10. **Empleados** - Pendiente módulos JS
11. **Contabilidad** - Pendiente módulos JS

## 📋 Patrón Estándar por App

Cada app debe tener:

### JS (apps/tenant/core/static/core/js/<app>/)
- `<app>.api.js` - Wrapper de endpoints DRF
- `<app>.ui.js` - Renderizado y eventos
- `<app>.page.js` - Entry point (`window.init<App>Page`)
- `<app>.components.js` (opcional) - Helpers de render

### Partials (apps/tenant/core/templates/tenant/core/partials/<app>/)
- `list.html` - Vista principal
- `form.html` (si aplica) - Crear/editar
- `detail.html` (si aplica) - Detalle read-only
- `modals.html` (si aplica) - Modales
- `assets_<app>.html` - Incluye JS en orden

### Router
- Ruta `#<app>` → `window.init<App>Page()`

## 🔗 Endpoints Identificados

### Inventario
- `GET /api/v1/inventario/catalogo/` (ViewSet)
- `GET /api/v1/core/inventario/resumen/` (Core API)
- `GET /api/v1/core/inventario/catalogo/` (Core API)
- `POST /api/v1/core/inventario/entrada/` (Core API)

### Gastos
- `GET /api/v1/gastos/` (ViewSet)
- `POST /api/v1/gastos/` (ViewSet)
- `GET /api/v1/gastos/{id}/` (ViewSet)
- `PATCH /api/v1/gastos/{id}/` (ViewSet)
- `DELETE /api/v1/gastos/{id}/` (ViewSet)

### Proveedores
- `GET /api/v1/proveedores/` (ViewSet)
- `POST /api/v1/proveedores/` (ViewSet)
- `GET /api/v1/proveedores/{id}/` (ViewSet)
- `PATCH /api/v1/proveedores/{id}/` (ViewSet)
- `DELETE /api/v1/proveedores/{id}/` (ViewSet)

### Empleados
- `GET /api/v1/empleados/empleados/` (ViewSet)
- `GET /api/v1/empleados/contratos/` (ViewSet)
- `GET /api/v1/empleados/afiliaciones/` (ViewSet)
- `GET /api/v1/empleados/devengos/` (ViewSet)
- `GET /api/v1/empleados/capacitaciones/` (ViewSet)

### Contabilidad
- `GET /api/v1/contabilidad/cuentas-contables/` (ViewSet)
- `GET /api/v1/core/contabilidad/cuentas/` (Core API)
- `GET /api/v1/core/contabilidad/asientos/` (Core API)
- `GET /api/v1/core/contabilidad/movimientos/` (Core API)

### Landing
- `GET /api/v1/core/landing/info/` (Core API)
- `GET /api/v1/core/landing/resumen/` (Core API)

## 📝 Notas

- Todas las apps deben usar `window.http()` de `lib/http.js`
- SessionAuth + CSRF en mutaciones
- Manejo de errores 409/422/415/400
- Sin `?async=true` en uploads
- Parse-only para documentos: `/api/v1/core/documentos/upload/?preview=true`
