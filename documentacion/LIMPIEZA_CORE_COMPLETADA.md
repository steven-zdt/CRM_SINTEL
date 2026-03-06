# ✅ Limpieza Core Completada

## Resumen Ejecutivo

Se eliminaron **14 archivos** legacy/duplicados de `apps/tenant/core`:
- **5 templates** duplicados/obsoletos
- **9 archivos JS** legacy/duplicados

## Archivos Eliminados

### Templates
1. `partials/assets_common.html` (vacío)
2. `partials/assets_facturas_refresh.html` (archivo inexistente)
3. `partials/assets_facturas.html` (duplicado)
4. `partials/assets_perfil.html` (duplicado)
5. `partials/assets_maildigester.html` (duplicado)

### Static JS
1. `facturas.ui.js` (legacy)
2. `empresa.ui.js` (legacy)
3. `perfil.ui.js` (legacy)
4. `contabilidad.ui.js` (legacy)
5. `dashboard.ui.js` (legacy)
6. `landing.ui.js` (legacy)
7. `landing.reset.ui.js` (legacy)
8. `http.js` (duplicado, usar lib/http.js)
9. `_csrf.js` (obsoleto)

## Cambios en workspace.html

✅ Actualizado `page_assets_body`:
- Eliminados includes de assets duplicados/obsoletos
- Agregados includes de todos los assets modulares (11 módulos)
- Agregado `router.js` al final

## Estructura Final

```
apps/tenant/core/
├── templates/tenant/core/
│   ├── workspace.html
│   └── partials/
│       └── <app>/ (11 módulos con assets)
└── static/core/js/
    ├── router.js ✅
    ├── lib/http.js ✅
    └── <app>/ (11 módulos modulares)
```

## Verificación

- ✅ 0 referencias a archivos eliminados (grep limpio)
- ✅ Todos los assets modulares incluidos en workspace.html
- ✅ Router.js incluido al final

## Próximos Pasos

1. Actualizar `workspace.html` a shell mínimo (eliminar JS inline y secciones legacy)
2. Migrar partials de inventario con guiones bajos al módulo modular
3. Pruebas smoke de navegación y CRUD
