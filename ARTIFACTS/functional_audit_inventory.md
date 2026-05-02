# Inventario Funcional - apps/tenant/core

## Fase 0: Preparación

### ✅ workspace.html
- **Estado**: ⚠️ **NO tiene `workspace-router-outlet`** - CRÍTICO
- **JS inline**: ⚠️ **SÍ tiene JS inline** (línea 767+) - debe eliminarse
- **Secciones legacy**: ⚠️ **SÍ tiene secciones `<section id="view-*">`** - deben eliminarse
- **Assets incluidos**: ✅ Todos los assets modulares incluidos
- **Router incluido**: ✅ `router.js` incluido al final

### ✅ lib/http.js
- **Estado**: ✅ Existe y está correcto
- **Funcionalidad**: ✅ `window.http()` con SessionAuth + CSRF
- **Manejo 401**: ✅ No crítico local

### ✅ router.js
- **Estado**: ✅ Existe y tiene todas las rutas
- **Rutas configuradas**: ✅ 12 rutas (empresa, facturas, mail, perfil, dashboard, contabilidad, inventario, empleados, gastos, proveedores, landing, clientes)

## Fase 1: Auditoría por App

| APP | PARTIALS | JS | assets_<app>.html | window.init<App>Page | RUTA ROUTER |
|-----|----------|----|-------------------|---------------------|-------------|
| empresa | ✅ assets_empresas.html | ✅ api/ui/page | ✅ OK | ✅ initEmpresaPage | ✅ #empresa |
| facturas | ✅ list.html, modals.html, assets_facturas.html | ✅ api/components/table/modals/page | ✅ OK | ✅ initFacturasPage | ✅ #facturas |
| inventario | ✅ assets_inventario.html + 4 partials legacy | ✅ api/ui/page | ✅ OK | ✅ initInventarioPage | ✅ #inventario |
| gastos | ✅ assets_gastos.html | ✅ api/ui/page | ✅ OK | ✅ initGastosPage | ✅ #gastos |
| landing | ✅ assets_landing.html | ✅ api/ui/page | ✅ OK | ✅ initLandingPage | ✅ #landing |
| perfil | ✅ assets_perfil.html | ✅ api/ui/page | ✅ OK | ✅ initPerfilPage | ✅ #perfil |
| proveedores | ✅ assets_proveedores.html | ✅ api/ui/page | ✅ OK | ✅ initProveedoresPage | ✅ #proveedores |
| empleados | ✅ assets_empleados.html | ✅ api/ui/page | ✅ OK | ✅ initEmpleadosPage | ✅ #empleados |
| dashboard | ✅ assets_dashboard.html | ✅ api/ui/page | ✅ OK | ✅ initDashboardPage | ✅ #dashboard |
| contabilidad | ✅ assets_contabilidad.html | ✅ api/ui/page | ✅ OK | ✅ initContabilidadPage | ✅ #contabilidad |
| mail | ✅ assets_mail.html | ✅ api/ui/page | ✅ OK | ✅ initMailDigesterPage | ✅ #mail |

## Issues Detectados

### 🔴 CRÍTICO
1. **workspace.html NO tiene `workspace-router-outlet`** - El router no puede montar vistas
2. **workspace.html tiene JS inline masivo** (línea 767+) - Debe eliminarse
3. **workspace.html tiene secciones legacy** (`<section id="view-*">`) - Deben eliminarse

### ⚠️ ADVERTENCIAS
1. **Inventario tiene partials legacy** (`_catalogo_table.html`, etc.) - Usados en workspace.html, migrar a módulo modular
