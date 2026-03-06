# Reporte de Limpieza Ejecutada - apps/tenant/core

## ✅ Archivos Eliminados

### Templates (5 archivos)
1. ✅ `partials/assets_common.html` - Vacío, no usado
2. ✅ `partials/assets_facturas_refresh.html` - Referencia archivo inexistente
3. ✅ `partials/assets_facturas.html` - Duplicado (ya existe en partials/facturas/)
4. ✅ `partials/assets_perfil.html` - Duplicado (ya existe en partials/perfil/)
5. ✅ `partials/assets_maildigester.html` - Duplicado (ya existe en partials/mail/)

### Static JS (9 archivos)
1. ✅ `facturas.ui.js` - Legacy, duplicado (ya existe modular en facturas/)
2. ✅ `empresa.ui.js` - Legacy, duplicado (ya existe modular en empresa/)
3. ✅ `perfil.ui.js` - Legacy, duplicado (ya existe modular en perfil/)
4. ✅ `contabilidad.ui.js` - Legacy, duplicado (ya existe modular en contabilidad/)
5. ✅ `dashboard.ui.js` - Legacy, duplicado (ya existe modular en dashboard/)
6. ✅ `landing.ui.js` - Legacy, duplicado (ya existe modular en landing/)
7. ✅ `landing.reset.ui.js` - Legacy, usa _csrf.js obsoleto
8. ✅ `http.js` - Duplicado (ES6 modules), usar lib/http.js (IIFE)
9. ✅ `_csrf.js` - Obsoleto, funcionalidad migrada a lib/http.js

## 📝 Cambios en workspace.html

### Actualizado `page_assets_body`:
- ❌ Eliminados includes de assets duplicados/obsoletos
- ✅ Agregados includes de todos los assets modulares
- ✅ Agregado `router.js` al final

### Assets Incluidos (en orden):
1. `empresa/assets_empresas.html`
2. `facturas/assets_facturas.html`
3. `mail/assets_mail.html`
4. `perfil/assets_perfil.html`
5. `dashboard/assets_dashboard.html`
6. `contabilidad/assets_contabilidad.html`
7. `inventario/assets_inventario.html`
8. `gastos/assets_gastos.html`
9. `proveedores/assets_proveedores.html`
10. `empleados/assets_empleados.html`
11. `landing/assets_landing.html`
12. `router.js` (al final)

## ⚠️ Archivos Mantenidos (REVIEW)

Los siguientes archivos se mantienen temporalmente porque están siendo usados en `workspace.html`:

1. `partials/inventario/_catalogo_table.html` - Usado en workspace.html línea 674
2. `partials/inventario/_catalogo_modals.html` - Usado en workspace.html línea 675
3. `partials/inventario/_activos_table.html` - Usado en workspace.html línea 408
4. `partials/inventario/_activos_modals.html` - Usado en workspace.html línea 409

**Nota**: Estos deberían migrarse al módulo modular de inventario cuando `workspace.html` se actualice a shell mínimo.

## 📊 Resumen

- **Total eliminado**: 14 archivos
- **Templates eliminados**: 5
- **JS eliminados**: 9
- **Archivos mantenidos (temporal)**: 4 partials de inventario

## ✅ Verificación Post-Limpieza

### Estructura Final Esperada:

```
apps/tenant/core/
├── templates/tenant/core/
│   ├── workspace.html (a actualizar a shell mínimo)
│   └── partials/
│       ├── empresa/assets_empresas.html ✅
│       ├── facturas/assets_facturas.html ✅
│       ├── facturas/list.html ✅
│       ├── facturas/modals.html ✅
│       ├── inventario/assets_inventario.html ✅
│       ├── inventario/_catalogo_table.html (temporal)
│       ├── inventario/_catalogo_modals.html (temporal)
│       ├── inventario/_activos_table.html (temporal)
│       ├── inventario/_activos_modals.html (temporal)
│       ├── gastos/assets_gastos.html ✅
│       ├── landing/assets_landing.html ✅
│       ├── perfil/assets_perfil.html ✅
│       ├── proveedores/assets_proveedores.html ✅
│       ├── empleados/assets_empleados.html ✅
│       ├── dashboard/assets_dashboard.html ✅
│       ├── contabilidad/assets_contabilidad.html ✅
│       └── mail/assets_mail.html ✅
└── static/core/js/
    ├── router.js ✅
    ├── lib/http.js ✅
    ├── empresa/ ✅
    ├── facturas/ ✅
    ├── inventario/ ✅
    ├── gastos/ ✅
    ├── landing/ ✅
    ├── perfil/ ✅
    ├── proveedores/ ✅
    ├── empleados/ ✅
    ├── dashboard/ ✅
    ├── contabilidad/ ✅
    └── mail/ ✅
```

## 🎯 Próximos Pasos

1. **Actualizar workspace.html a shell mínimo**:
   - Eliminar todo el JS inline
   - Eliminar todas las secciones `<section id="view-*">` legacy
   - Dejar solo navbar y `<div id="workspace-router-outlet"></div>`

2. **Migrar partials de inventario**:
   - Mover `_catalogo_table.html`, `_catalogo_modals.html`, etc. al módulo modular
   - Actualizar `inventario.page.js` para usar estos partials

3. **Pruebas Smoke**:
   - Navegar a cada hash `/#<app>`
   - Verificar que se monta la vista
   - Probar CRUD básico
   - Verificar CSRF en mutaciones
