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
  // redirect_url en login exitoso es "/dashboard/" (apps/tenant/core/api/viewsets.py:548),
  // que a su vez redirige server-side a /static/tenant/core/dashboard/index.html --
  // doble salto, 10s eran insuficientes en la practica (timeout real observado
  // con la pagina ya completamente cargada en la captura de pantalla).
  await page.waitForURL(/\/(dashboard|workspace|console|clientes)\/?/, { timeout: 20000 });
}

/**
 * Helper para detectar errores en la consola del navegador
 * @param {Page} page - Página de Playwright
 * @param {string} context - Contexto para logs
 * @param {string[]} ignorePatterns - Substrings de errores conocidos y ya
 *   documentados como fuera de alcance (no bugs de esta app) -- p.ej. el
 *   timing interno de Bootstrap Offcanvas ("null.scroll", ya documentado
 *   como excepcion aceptada para devengo_editor.js en F31.2, no algo que
 *   este spec deba "arreglar"). No usar para ocultar errores reales.
 * @returns {Function} Función para verificar errores acumulados
 */
async function expectNoConsoleErrors(page, context = '', ignorePatterns = []) {
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
    const relevantes = errors.filter((e) => !ignorePatterns.some((p) => e.includes(p)));
    expect(relevantes, relevantes.join('\n')).toHaveLength(0);
  };
}

module.exports = { login, expectNoConsoleErrors };
