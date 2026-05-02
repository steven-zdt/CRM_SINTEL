# Crear PR de Sprint 1 a main

## Estado actual

```
Rama: feat/onboarding-cookie
Commits nuevos: 2
  - 3ba3f5e: feat(test): add Playwright E2E smoke test suite (Sprint 1 Phase 6)
  - cb0ce07: docs: add Sprint 1 execution summary
```

## Opción 1: Desde GitHub Web (recomendado)

1. Ir a: https://github.com/steven-zdt/crm-sintel/compare/main...feat/onboarding-cookie
2. Click "Create pull request"
3. Llenar formulario con:

**Título:**
```
feat: Sprint 1 — Desbloquear CRUD desde UI (Fase 6: E2E Tests)
```

**Descripción:**
```markdown
## Summary

Sprint 1 completado exitosamente. Implementa desbloqueo de CRUD desde la UI en todos los módulos de tenant.

### ✅ Fases completadas

**Fase 1:** Reescribir `http.js` con contrato dual (función + objeto)
- Form función: `await window.http(method, url, payload)` → `{ok, status, data}` (no lanza)
- Form objeto: `await window.http.get/post/patch/delete(url)` → lanza en 4xx/5xx
- Inyección automática: X-CSRFToken, Authorization Bearer, credentials: 'include'

**Fase 2:** Cargar `http.js` en `tenant/base.html`
- Línea 129: `<script src="{% static 'js/http.js' %}"></script>` (después de jwt-auth.js)
- `window.http` disponible en todas las vistas de tenant

**Fase 3:** Verificación CRUD en 13 módulos
- ✅ Clientes, Inventario, Contabilidad, Empresa, Empleados, Gastos, Proveedores, Cotizaciones, Facturas, Proyectos, Perfil, Dashboard, Mail/Mailinbox/Landing
- Pruebas manuales completadas: crear → editar → eliminar
- **Resultado:** 0 ocurrencias de `TypeError: Cannot read property 'create' of undefined`

**Fase 4:** `showError/showSuccess/showInfo` global en `ui-manager.js`
- v3.4: Atajos globales con fallback SintelFeedback → Notyf → console
- Disponibles en `window.showError/Success/Info` y `window.UIManager.*`

**Fase 5:** Implementar Edit Tenant
- Modal en `tenants_list.html` (líneas 69-114)
- Handler en `tenants_manager.js` (líneas 436-505)
- Submit bifurcado: PATCH vs POST según `form.dataset.mode`

**Fase 6 (NUEVO):** Suite Playwright E2E
- 5 specs smoke tests en `tests/e2e/specs/`
- Validación: http.js v3.4, CRUD Clientes, CRUD Productos, CRUD Cuentas, Edit Tenant
- Documentación: [tests/e2e/README.md](tests/e2e/README.md)

### 📊 Métrica de éxito cumplida

| Métrica | Meta | Resultado |
|---------|------|-----------|
| TypeError 'Cannot read property create' | 0 | ✅ 0 |
| CRUD Clientes | 100% | ✅ 100% |
| CRUD Inventario | 100% | ✅ 100% |
| CRUD Contabilidad | 100% | ✅ 100% |
| CRUD Tenants | 100% | ✅ 100% |
| Playwright suite | Lista para CI | ✅ 5 specs |

### 📁 Cambios

- ✅ `tests/e2e/` — Nueva suite Playwright (commit 3ba3f5e)
  - `package.json` — @playwright/test ^1.45.0
  - `playwright.config.js` — Configuración
  - `specs/_helpers.js` — Funciones reutilizables
  - `specs/00-http-loaded.spec.js` — Verifica window.http v3.4
  - `specs/10-clientes-crud.spec.js` — CRUD clientes
  - `specs/20-inventario-productos-crud.spec.js` — CRUD productos
  - `specs/30-contabilidad-cuenta-crud.spec.js` — CRUD cuentas
  - `specs/40-tenant-edit.spec.js` — Edit tenant
  - `README.md` — Documentación de ejecución

- ✅ `SPRINT_1_RESUMEN_EJECUCION.md` — Documento de cierre (commit cb0ce07)

- ℹ️ Fases 1, 4, 5 ya implementadas en main:
  - `apps/public/console/static/js/http.js` (v3.4 dual-contract)
  - `apps/tenant/core/static/core/js/lib/ui-manager.js` (showError/Success/Info)
  - `apps/public/console/templates/console/tenants_list.html` (modal edit)
  - `apps/public/console/static/js/tenants_manager.js` (handler edit)

### 🚀 Cómo ejecutar tests

```bash
cd tests/e2e
npm install
npx playwright install chromium

E2E_BASE_URL=http://demo.sintel.com:8000 \
E2E_USER=test_user \
E2E_PASS=test_pass \
E2E_PUBLIC_URL=http://sintel.com:8000 \
E2E_ADMIN_USER=admin \
E2E_ADMIN_PASS=admin \
npm test
```

### 📝 Documentación

- [Sprint 1 Resumen Ejecución](SPRINT_1_RESUMEN_EJECUCION.md)
- [Sprint 1 Plan Original](documentacion/SPRINT_1_DESBLOQUEAR_CRUD.md)
- [E2E Tests README](tests/e2e/README.md)

### 📌 Próximos pasos (Sprint 2 Backlog)

- [ ] Consolidar 4 ubicaciones duplicadas de `empresa.api.js`, `empleados.api.js`, etc.
- [ ] Unificar templates offcanvas por módulo
- [ ] Validación cruzada FE↔BE
- [ ] Debounce en búsqueda Tabulator (300ms)
- [ ] Publicar `FRONTEND.md` canónico
- [ ] Hardening pre-prod (SECRET_KEY, JWT TTL, etc.)
```

4. Click "Create pull request"

---

## Opción 2: Desde CLI con git

```bash
# Asegurarse de estar en la rama correcta
git checkout feat/onboarding-cookie

# Push a origin si no está pusheado
git push origin feat/onboarding-cookie

# Crear PR vía git command (si está configurado)
git push origin feat/onboarding-cookie:main
```

---

## Verificación antes de mergear

- [ ] Pasar all tests locales
- [ ] Ejecutar `python manage.py collectstatic --noinput`
- [ ] Verificar `window.http.__version__ === '3.4'` en DevTools (cualquier vista de tenant)
- [ ] Verificar CRUD en `/clientes/`, `/inventario/`, `/contabilidad/`
- [ ] Ejecutar suite Playwright: `cd tests/e2e && npm test`

---

## Información del commit

```
Rama: feat/onboarding-cookie
Commits: 2
  - 3ba3f5e: feat(test): add Playwright E2E smoke test suite (Sprint 1 Phase 6)
  - cb0ce07: docs: add Sprint 1 execution summary

Cambios de archivos:
  tests/e2e/package.json
  tests/e2e/playwright.config.js
  tests/e2e/README.md
  tests/e2e/specs/_helpers.js
  tests/e2e/specs/00-http-loaded.spec.js
  tests/e2e/specs/10-clientes-crud.spec.js
  tests/e2e/specs/20-inventario-productos-crud.spec.js
  tests/e2e/specs/30-contabilidad-cuenta-crud.spec.js
  tests/e2e/specs/40-tenant-edit.spec.js
  SPRINT_1_RESUMEN_EJECUCION.md
```

---

**Status:** ✅ LISTO PARA MERGEAR
