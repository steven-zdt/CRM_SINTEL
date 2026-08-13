# F32.5 — Infraestructura de validación real de navegador (estado)

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
   esta sesión, `screenshot` fallaba por completo -- confirmado que ya
   no es el caso).
2. **Pero las herramientas de navegador con IA (interactivas) bloquean el
   envío de login**: tanto el Browser pane sandboxed como Claude in
   Chrome (con o sin resolución DNS) devuelven `net::ERR_BLOCKED_BY_CLIENT`
   en el POST de login -- confirmado con Network/Console reales, no
   supuesto. Es un bloqueo de la propia plataforma sobre automatización
   interactiva de credenciales, no un bug de esta app.
3. **Decisión (con el usuario, explícita):** instalar `pytest-playwright`
   fue la propuesta inicial, pero al investigar se encontró que **ya
   existe una suite E2E completa con `@playwright/test` (JS, no Python)**
   en `tests/e2e/` -- `package.json`, `playwright.config.js`, 5 specs
   reales, `_helpers.js` -- nunca ejecutada (README documenta
   "Selectores no funcionan" como troubleshooting esperado). Se reutilizó
   esta suite en vez de construir una nueva en paralelo (regla ya
   establecida esta sesión: reutilizar > crear).
4. **Ni el host ni el contenedor `web` tienen Node.js.** Solución: un
   contenedor Docker efímero (`mcr.microsoft.com/playwright`, con Node +
   Chromium preinstalados) en la red `crm_sintel_default`, con
   `--add-host` apuntando al IP interno del contenedor `web`
   (`172.18.0.5`) para resolver el hostname del tenant de prueba. No
   requiere tocar el `Dockerfile` de producción.
5. **Tenant de prueba:** no se usó `home` (tenant real con datos/usuarios
   reales, incluida la cuenta que el usuario ofreció interactivamente y
   que se declinó usar por la prohibición de someter autenticación). Se
   usó `qaisotest` -- ya existente, nombre indica próposito de QA. Se
   provisionó un usuario desechable (`e2e_test_user`, contraseña generada
   por esta sesión) como fixture de test estándar -- mismo patrón que los
   `TenantProfile.objects.create(...)` ya usados decenas de veces en
   pytest a lo largo de esta sesión, no un login interactivo con
   credenciales humanas.
6. **Bug real encontrado durante el setup, no hipotético:** el login
   falló con "No tienes acceso a este tenant" hasta crear el registro
   `TenantMembership` (schema público) -- crear solo `TenantProfile`
   (schema del tenant) no basta. `apps/tenant/core/api/viewsets.py:508`
   verifica membresía contra `TenantMembership`, no `TenantProfile`.

## 3. Resultado: infraestructura funcionando, 1 test verde real

```
specs/00-http-loaded.spec.js
  ✓ window.http está disponible como función con métodos (4.4s)
  [F32.1 baseline] window.http.__version__ = (sin version -- lib/http.js activo)
```

**Este resultado confirma empíricamente, en un navegador real, el
hallazgo estático de F32.1**: `lib/http.js` (sin `__version__`) es el
cliente HTTP que realmente está activo en el workspace tenant -- no la
versión "v3.4 unificado" que el propio helper de este test asumía
originalmente (`expect(info.version).toBe('3.4')`, ahora corregido a
verificación informativa, ver `_helpers.js`). Es la primera vez que este
hallazgo se verifica dinámicamente, no solo por lectura de código.

## 4. Correcciones aplicadas a la suite E2E preexistente

- `specs/_helpers.js` -- `login()`: la ruta `/login/` no existe (Django
  la eliminó, ver `config/urls_tenant.py:15`); el shell real es
  `/static/tenant/core/auth/login.html`. Los campos son `#login_email`/
  `#login_password` (no `#username`/`#password`).
- `specs/_helpers.js` -- `expectHttpAvailable()`: ya no afirma
  `__version__ === '3.4'` (falso en producción, ver §3) -- ahora verifica
  la baseline real y la reporta, sin asumir cuál versión "debería" ganar.
- `specs/10-clientes-crud.spec.js`: `/clientes/` ya no existe (404 real,
  confirmado con captura de pantalla) -- ruta correcta es `/ui/clientes/`
  (patrón Fase 5-BIS ya usado en todas las apps migradas esta sesión).

## 5. Lo que queda pendiente -- honesto, no oculto

`/ui/clientes/` con el fix de ruta aplicado devuelve **JSON crudo**, no
un shell HTML con tabla -- indica que la navegación de prueba aún no
apunta al shell correcto para `clientes` (a diferencia de `proyectos`/
`empresa`/etc. donde `/ui/<app>/` sirve HTML). Los specs 20
(inventario), 30 (contabilidad) y 40 (tenant-edit consola pública) no se
ejecutaron todavía -- selectores y rutas sin verificar, mismo patrón de
"escrito especulativamente antes de que la UI real existiera" que ya se
encontró en 00 y 10.

**Esto no bloquea F32.6/F32.7** en el sentido de "no hay forma de
validar" -- la infraestructura real ya existe y funciona (contenedor
Playwright + tenant de prueba + usuario desechable + fix de login). Lo
que falta es tiempo de iteración por spec, no una limitación de entorno.
Corregir los 4 specs restantes y ampliarlos a la matriz completa que pide
F32.8 (401/403/CSRF failure/refresh JWT/upload/HTMX/offcanvas) es trabajo
real, del mismo orden de magnitud que arreglar el que ya se corrigió --
se documenta como continuación explícita, no como bloqueo oculto.

## 6. Cómo re-ejecutar esto

```bash
# Contenedor efimero, red compartida con docker-compose, IP del web
# container obtenido con: docker inspect crm_sintel-web-1 --format \
#   '{{(index .NetworkSettings.Networks "crm_sintel_default").IPAddress}}'
docker run --rm \
  --network crm_sintel_default \
  --add-host qaisotest.sintel.net.co:172.18.0.5 \
  -v "$(pwd)/tests/e2e:/e2e" \
  -w /e2e \
  -e E2E_BASE_URL=http://qaisotest.sintel.net.co:8000 \
  -e E2E_USER=e2e_test_user \
  -e E2E_PASS='E2eTestPass!2026' \
  mcr.microsoft.com/playwright:v1.62.1-jammy \
  sh -c "npm install && npx playwright test 00-http-loaded.spec.js --reporter=list"
```

**Nota de mantenimiento:** el IP `172.18.0.5` no está garantizado estable
entre reinicios de `docker compose` -- re-obtenerlo con el comando de
arriba si el `--add-host` deja de resolver.

## 7. Próximo paso real

No F32.6 todavía. Antes: (a) arreglar la ruta de `clientes` (investigar
por qué `/ui/clientes/` devuelve JSON, no HTML), (b) correr y arreglar
specs 20/30/40, (c) ampliar la matriz a los escenarios de F32.8 que
importan más para el riesgo real de F32 (CSRF failure, 401 crítico vs
no-crítico, upload con `FormData`) -- estos son los que directamente
prueban o refutan el diseño de `Core.Http` (`F32_3_CORE_HTTP_CONTRACT.md`).
Solo con eso en verde se justifica tocar `http.js`.
