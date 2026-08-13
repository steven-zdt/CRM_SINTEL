const { expect } = require('@playwright/test');

/**
 * Login helper — inicia sesión en el sistema
 * @param {Page} page - Página de Playwright
 * @param {Object} credentials - { username, password }
 */
async function login(page, { username, password }) {
  // Fase F32.5: corregido contra el login real (verificado en navegador real,
  // no supuesto). No existe ruta Django /login/ -- el shell de login vive en
  // /static/tenant/core/auth/login.html (config/urls_tenant.py:84, redirect
  // desde /). Usa email (no username) y hace fetch()+redirect_url via JS, no
  // un submit de formulario nativo -- pero la navegacion via
  // window.location.href si dispara waitForURL igual.
  await page.goto('/static/tenant/core/auth/login.html');
  await page.fill('#login_email', username);
  await page.fill('#login_password', password);
  await page.click('#login_submit_btn');
  // redirect_url en login exitoso es "/dashboard/" (apps/tenant/core/api/viewsets.py:548)
  await page.waitForURL(/\/(dashboard|workspace|console|clientes)\/?/, { timeout: 10000 });
}

/**
 * Helper para detectar errores en la consola del navegador
 * @param {Page} page - Página de Playwright
 * @param {string} context - Contexto para logs
 * @returns {Function} Función para verificar errores acumulados
 */
async function expectNoConsoleErrors(page, context = '') {
  const errors = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      errors.push(`[${context}] ${msg.text()}`);
    }
  });

  page.on('pageerror', (err) => {
    errors.push(`[${context}] ${err.message}`);
  });

  // Retorna una función que verifica los errores acumulados
  return () => {
    expect(errors, errors.join('\n')).toHaveLength(0);
  };
}

/**
 * Helper para verificar que window.http esté disponible y correctamente configurado
 * @param {Page} page - Página de Playwright
 */
async function expectHttpAvailable(page) {
  // Fase F32.1: la suposicion original de este helper ("v3.4 esta activo,
  // __version__ === '3.4'") es FALSA en produccion -- el orden de carga real
  // (tenant/base.html:129 carga http.js v3.4 primero, workspace.html via
  // assets_core.html carga core/js/lib/http.js despues y lo sobreescribe,
  // ver documentacion/F32_1_2_TRANSPORT_AUDIT.md S2) hace que la version SIN
  // __version__ (lib/http.js) sea la que realmente gana. Este check ahora
  // verifica la baseline real (funcion global window.http disponible como
  // funcion invocable), no la version especifica -- asercion sobre
  // __version__ se reintroduce en F32.7 una vez Core.Http sea el unico
  // ganador confirmado.
  const info = await page.evaluate(() => ({
    type: typeof window.http,
    version: window.http && window.http.__version__,
  }));

  expect(info.type).toBe('function');
  // Documentar cual version esta activa ahora mismo (visible en el reporte
  // del test, no en aserciones -- es informativo para el audit, no un fallo).
  console.log(`[F32.1 baseline] window.http.__version__ = ${info.version === undefined ? '(sin version -- lib/http.js activo)' : info.version}`);
}

module.exports = { login, expectNoConsoleErrors, expectHttpAvailable };
