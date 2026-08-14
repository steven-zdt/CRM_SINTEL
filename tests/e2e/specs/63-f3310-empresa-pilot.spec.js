const { test, expect } = require('@playwright/test');
const { login } = require('./_helpers');

// F33.10: piloto empresa. Verifica que:
// 1. El offcanvas "Nueva Sede" (via sintelAbrirOffcanvasEmpresa, ahora un
//    alias delgado de Sintel.Core.mostrarOffcanvasSeguro tras F33.4) abre
//    correctamente en un flujo real de click, no solo la unidad aislada
//    del spec 62.
// 2. Los 2 templates de modal muerto eliminados (empresa/modals.html,
//    mailinbox_modals.html) no dejan huecos -- la pagina carga sin error.

const username = process.env.E2E_USER || 'test_user';
const password = process.env.E2E_PASS || 'test_pass';

// NOTA: se descarto un primer test que verificaba "0 errores de red/consola"
// en toda la carga de /workspace/#empresa -- el flujo de login() (F32.5,
// _helpers.js) pasa siempre por un redirect intermedio a /dashboard/, que
// a su vez sirve el shell estatico independiente
// (static/tenant/core/dashboard/index.html) con su propio <script>
// hardcodeado hacia core/js/lib/http.js -- archivo eliminado
// deliberadamente en F32.7 (commit 720b769, documentado explicitamente
// como "esa pagina ya esta rota por separado"). Ese 404 ocurre en TODO
// test E2E que llama login() desde F32.7 en adelante, sin relacion con
// este pilot -- no es un hallazgo de F33.10, solo confirma la nota ya
// escrita en F32.7.

test('F33.10: "Nueva Sede" abre el offcanvas via el helper consolidado (sintelAbrirOffcanvasEmpresa)', async ({ page }) => {
  await login(page, { username, password });
  await page.goto('/workspace/#empresa');
  await page.waitForSelector('#tab-empresa', { state: 'visible', timeout: 10000 });

  // Activar el sub-tab Sedes (Bootstrap tab, no HTMX).
  await page.click('#empresa-sedes-tab');
  await page.waitForSelector('#subtab-sedes.active, #subtab-sedes.show', { timeout: 5000 }).catch(() => {});

  await page.click('button:has-text("Nueva Sede")');
  await page.waitForSelector('#offcanvas-sede.show', { state: 'visible', timeout: 10000 });

  const isVisible = await page.isVisible('#offcanvas-sede.show');
  expect(isVisible).toBe(true);
});
