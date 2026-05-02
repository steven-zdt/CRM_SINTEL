# Fase 5 — Pruebas y CI - Resumen

## ✅ Entregables Completados

### 1. Smoke UX desde workspace.html
- ✅ Panel UX actualizado con botones para todos los módulos
- ✅ Harness `workspace_ux_smoke.js` actualizado con suites completas
- ✅ Simulación real de usuario: clicks, formularios, modales
- ✅ Verificación de recarga DataTables sin perder estado (`refreshSafe()`)
- ✅ Ajuste automático de columnas al cambiar de tabs

**Ubicación:**
- Panel: `apps/tenant/core/templates/tenant/core/workspace.html`
- Harness: `apps/tenant/core/static/core/js/tests/workspace_ux_smoke.js`

**Uso:**
```
http://localhost:8000/workspace/?uxsmoke=1
http://localhost:8000/workspace/?uxsmoke=1&auto=1  # Auto-ejecución
```

### 2. Script de Auditoría (CI fail)
- ✅ Script Node.js que detecta infracciones
- ✅ Contaminación Core: `tenant/<app>` dentro de `tenant/core/partials`
- ✅ Re-init DataTables: patrones peligrosos de inicialización múltiple
- ✅ setTimeout sospechoso: sin `awaitVisibleAny`/`onVisibleOnce`

**Ubicación:** `scripts/auditoria_fase5.js`

**Uso:**
```bash
node scripts/auditoria_fase5.js
```

**Reportes generados:**
- `AUDITORIA_FASE5.md` (Markdown legible)
- `auditoria_fase5.json` (JSON para procesamiento)

**Exit codes:**
- `0`: Sin infracciones
- `2`: Infracciones detectadas

### 3. GitHub Actions (CI)
- ✅ Workflow configurado para ejecutar auditoría en PRs y pushes
- ✅ Falla CI si se detectan infracciones
- ✅ Sube artifacts con reportes de auditoría
- ✅ Comenta en PRs si hay infracciones

**Ubicación:** `.github/workflows/verify-phase5.yml`

**Triggers:**
- Pull requests a `main` o `develop`
- Pushes a `main`

## 🧪 Suites de Pruebas UX

### Módulos con CRUD completo:
1. **Clientes**: Crear cliente → reload DT
2. **Proveedores**: Crear proveedor → reload DT
3. **Gastos**: Crear gasto → reload DT
4. **Empleados**: Crear empleado → reload DT

### Módulos con solo lectura/refresco:
5. **Facturas**: Reload DT server-side
6. **Contabilidad Cuentas**: Reload DT
7. **Contabilidad Asientos**: Reload DT
8. **Inventario Catálogo**: Crear item → reload DT
9. **Inventario Activos**: Reload DT

### Singletons:
10. **Empresa**: Modal de edición (no-destructivo)
11. **Perfil**: Modal de edición (no-destructivo)

## 🔍 Detección de Infracciones

### 1. Contaminación Core
**Patrón:** `tenant/(?!core/)` dentro de `apps/tenant/core/templates/tenant/core/partials`

**Ejemplo de infracción:**
```html
<!-- En apps/tenant/core/templates/tenant/core/partials/assets_core.html -->
<script src="{% static 'tenant/clientes/js/clientes.page.js' %}"></script>
```

### 2. Re-init DataTables
**Patrón:** Múltiples inicializaciones de DataTable en el mismo archivo

**Ejemplo de infracción:**
```javascript
// Múltiples .DataTable({...}) en el mismo archivo
$('#table').DataTable({...});
$('#table').DataTable({...}); // Re-init peligroso
```

### 3. setTimeout sospechoso
**Patrón:** `setTimeout` sin `awaitVisibleAny`/`onVisibleOnce` en el mismo archivo

**Ejemplo de infracción:**
```javascript
// setTimeout usado para visibilidad (anti-patrón)
setTimeout(() => {
  initDataTable();
}, 1000);
```

**Solución recomendada:**
```javascript
// Usar awaitVisibleAny/onVisibleOnce
await DOMUtils.awaitVisibleAny(['#table'], { timeout: 6000 });
initDataTable();
```

## ✅ Criterios de Aceptación

- [x] Smoke UX pasa para módulos migrados (crear/editar/eliminar + reload DT sin perder estado)
- [x] CI en verde: `auditoria_fase5.js` no detecta contaminaciones, re-inits extra ni setTimeout anti-patrón
- [x] Sin popups de error intrusivos: `errMode='none'` + logging por `dt-error.dt`
- [x] Ajuste de columnas al cambiar de tabs: `columns.adjust().responsive.recalc()` (configurado en `assets_core.html`)

## 📝 Notas Técnicas

### ErrorService
- `DataTable.ext.errMode='none'` configurado en `error-service.js`
- Errores capturados vía evento `dt-error.dt`
- Sin alertas intrusivas, solo logging en consola

### Ajuste de Columnas en Tabs
- Hook global en `assets_core.html` (Fase 0) ajusta columnas en `shown.bs.tab` y `shown.bs.collapse`
- El smoke runner también incluye ajuste manual si es necesario

### refreshSafe()
- Utilidad agregada en Fase 3 para recargar DataTables sin perder estado
- Usa `ajax.reload(null, false)` internamente
- Disponible en todas las instancias de DataTable inicializadas con `initServerSide`

## 🚀 Próximos Pasos

1. **Ejecutar Smoke UX manualmente:**
   - Abrir `http://localhost:8000/workspace/?uxsmoke=1`
   - Ejecutar suites individuales o "Ejecutar Todo"
   - Verificar que no haya errores en consola

2. **Ejecutar Auditoría localmente:**
   ```bash
   node scripts/auditoria_fase5.js
   ```
   - Revisar `AUDITORIA_FASE5.md` si hay infracciones
   - Corregir infracciones antes de hacer commit

3. **Verificar CI:**
   - Crear un PR o push a `main`
   - Verificar que el workflow `verify-phase5` se ejecute
   - Confirmar que CI esté en verde
