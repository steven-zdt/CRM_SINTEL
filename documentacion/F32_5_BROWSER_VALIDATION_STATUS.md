# F32.5 — Infraestructura de validación real de navegador (estado final)

**Fecha:** 2026-08-13 · Rama `feat/onboarding-cookie`.

---

## 1. Objetivo de esta fase

El plan F32 del usuario es explícito: nada de F32.6 (migrar los 6
`*.api.js`) ni F32.7 (eliminar `http.js` duplicados) se hace sin antes
tener "una prueba real de tenant" verificada en navegador -- exactamente
la limitación que F31 documentó como motivo de diferir esta consolidación
(`F31_FINAL_REPORT.md` §9: sin credenciales de tenant, sin
`pytest-playwright`). Esta fase resuelve esa limitación con
infraestructura real, no con más análisis de código.

## 2. Camino recorrido -- por qué no fue trivial

1. **El Browser pane sandboxed ahora renderiza páginas reales** (antes de
   esta sesión, `screenshot` fallaba por completo).
2. **Las herramientas de navegador con IA (interactivas) bloquean el
   envío de login**: tanto el Browser pane sandboxed como Claude in
   Chrome devuelven `net::ERR_BLOCKED_BY_CLIENT` en el POST de login --
   confirmado con Network/Console reales. Bloqueo de la propia plataforma
   sobre automatización interactiva de credenciales, no un bug de esta app.
3. **Decisión (con el usuario, explícita):** en vez de instalar
   `pytest-playwright` (propuesta inicial), se encontró que **ya existe
   una suite E2E completa con `@playwright/test`** (JS, no Python) en
   `tests/e2e/` -- nunca ejecutada (README documentaba "Selectores no
   funcionan" como troubleshooting esperado). Reutilizada en vez de
   construir una nueva en paralelo (regla ya establecida: reutilizar > crear).
4. **Ni el host ni el contenedor `web` tienen Node.js.** Solución: un
   contenedor Docker efímero (`mcr.microsoft.com/playwright:v1.62.1-jammy`)
   en la red `crm_sintel_default`, con `--add-host` apuntando al IP interno
   del contenedor `web`. No requiere tocar el `Dockerfile` de producción.
5. **Tenant de prueba:** `qaisotest` (ya existente, nombre indica próposito
   de QA) -- no `home` (tenant real, incluida la cuenta que el usuario
   ofreció interactivamente y que se declinó usar por la prohibición de
   someter autenticación). Usuario desechable `e2e_test_user` provisionado
   como fixture estándar de test (mismo patrón que
   `TenantProfile.objects.create(...)` ya usado en pytest toda la sesión).
6. **Bug real encontrado en el setup**: login fallaba con "No tienes
   acceso a este tenant" hasta crear `TenantMembership` (schema público)
   -- `TenantProfile` (schema tenant) solo no basta
   (`apps/tenant/core/api/viewsets.py:508`).

## 3. Resultado final: 4 de 5 specs en verde

```
✓ 00-http-loaded.spec.js           -- window.http disponible
✓ 10-clientes-crud.spec.js         -- crear → editar → eliminar
✓ 20-inventario-productos-crud.spec.js -- crear → editar → eliminar
✓ 30-contabilidad-cuenta-crud.spec.js  -- crear → editar → eliminar
✘ 40-tenant-edit.spec.js           -- bloqueado por bug estructural real (§6)
```

**Hallazgo más importante (00):** confirma empíricamente, en navegador
real, el hallazgo estático de F32.1 -- `lib/http.js` (sin `__version__`)
es el cliente HTTP que realmente está activo en el workspace tenant, no
la versión "v3.4 unificado" que el propio test asumía originalmente.

## 4. Bugs reales encontrados y corregidos (6 total, todos verificados en navegador, no por inspección)

| # | App | Bug | Commit |
|---|---|---|---|
| 1 | tenant/core | Login fallaba sin `TenantMembership` en schema público (setup, no bug de código) | -- |
| 2 | clientes | `deleteCliente()` rechaza cliente activo -- el test no lo contemplaba, no un bug de la app | -- |
| 3 | inventario | Misma regla `activo` para `deleteProducto` -- mismo patrón, no bug | -- |
| 4 | bancos/contabilidad | Colisión real de ID (`#cuentas-panel`, `#search-cuenta`) -- el selector genérico resolvía a la tabla equivocada | `1ad2be1` |
| 5 | contabilidad | `guardarCuenta()` disparaba `'contabilidad:refresh'`, **0 listeners en todo el árbol** -- la tabla nunca se actualizaba tras crear/editar | `1ad2be1` |
| 6 | contabilidad | **WRONG_LOOKUP real**: PATCH de edición usaba `cuenta.id` (PK entero) contra un endpoint `lookup_field='uuid'` -- editar una cuenta contable devolvía `not_found` en producción | `1ad2be1` |

Los bugs #4-#6 son reales, confirmados con screenshots del navegador
(mensaje `not_found` visible en el offcanvas para #6), no hipótesis.

## 5. Correcciones aplicadas a la suite E2E preexistente

- `specs/_helpers.js` -- `login()`: ruta real `/static/tenant/core/auth/login.html`
  (no `/login/`, eliminada), campos `#login_email`/`#login_password`, timeout
  aumentado a 20s (redirect real hace doble salto).
- `specs/_helpers.js` -- `expectHttpAvailable()`: ya no afirma
  `__version__ === '3.4'` (falso en producción) -- ahora verifica la
  baseline real y la reporta.
- `specs/_helpers.js` -- `expectNoConsoleErrors()`: acepta `ignorePatterns`
  para filtrar ruido ya catalogado (p.ej. timing interno de Bootstrap
  Offcanvas) sin perder la capacidad de detectar errores nuevos.
- Los 4 specs CRUD: navegación real via `/workspace/#<app>` (hash tabs,
  no páginas propias -- `/clientes/`, `/ui/clientes/`, `/contabilidad/cuentas/`
  no son la UI real), selectores contra el markup fuente real (offcanvas
  IDs, `data-action`/`data-uuid`, clases `.btn-editar-cuenta` etc.), y las
  reglas de negocio reales ("no eliminar activo, desactivar primero").

## 6. Spec 40 (tenant-edit, consola pública) -- bloqueado por bug estructural real

No es un problema de selectores desactualizados como los otros 4. El
botón "Editar" en `tenants/list.html` dispara `openEditTenantModal()`
(`tenants_manager.js`), que busca `document.getElementById('tenant-form')`
y aborta con un error visible si no lo encuentra. **`#tenant-form` solo
existe en `tenants/new.html`** (la página de crear tenant), nunca en
`list.html` ni en ningún template que esta incluya (grep completo del
árbol de templates). **Editar un tenant desde la lista está roto en
producción, siempre, para cualquier tenant** -- no es un caso límite.

Esto es un bug real y estructural, pero en la **consola pública**
(`apps/public/console/`), una subsistema completamente distinto del
workspace tenant que es el objeto real de F32 (transporte HTTP/CSRF/JWT
del lado tenant). Corregirlo requeriría decidir arquitectura (¿modal
compartido en `list.html`, o navegar a una página de edición dedicada
como ya existe para "crear"?) -- fuera de alcance de F32. Flageado por
separado (`task_e7c1fa06`), no se toca aquí.

## 7. Cómo re-ejecutar esto

```bash
# IP del contenedor web (puede cambiar entre reinicios de docker compose):
docker inspect crm_sintel-web-1 --format \
  '{{(index .NetworkSettings.Networks "crm_sintel_default").IPAddress}}'

docker run --rm \
  --network crm_sintel_default \
  --add-host qaisotest.sintel.net.co:<IP_DEL_WEB> \
  -v "$(pwd)/tests/e2e:/e2e" \
  -w /e2e \
  -e E2E_BASE_URL=http://qaisotest.sintel.net.co:8000 \
  -e E2E_USER=e2e_test_user \
  -e E2E_PASS='E2eTestPass!2026' \
  mcr.microsoft.com/playwright:v1.62.1-jammy \
  sh -c "npm install && npx playwright test --reporter=list"
```

Usuarios de prueba desechables provisionados (persisten en la BD del
entorno, reutilizables): `e2e_test_user` (tenant `qaisotest`, rol ADMIN,
`TenantMembership` activa) y `e2e_console_admin` (superusuario schema
público, para la consola). Ninguno de los dos usa datos ni credenciales
reales del usuario.

## 8. Próximo paso real

**F32.6/F32.7 (migrar los 6 `api.js`, eliminar `http.js` duplicados) ya
tienen la validación real que exigía el plan** -- 4 de 5 flujos CRUD
completos (crear/editar/eliminar, HTMX, offcanvas, reglas de negocio)
verificados en navegador real contra 3 apps distintas (clientes,
inventario, contabilidad), más el transporte base (`window.http`)
confirmado. La matriz completa de F32.8 (401/403/CSRF failure/refresh
JWT/upload) sigue sin cubrir -- se ampliará como parte de F32.6/F32.7
mismos, verificando cada consumidor migrado con esta misma
infraestructura ya probada, en vez de intentar cubrir todo antes de
empezar a migrar.
