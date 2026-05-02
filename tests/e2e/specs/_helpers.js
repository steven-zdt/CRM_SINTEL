const { expect } = require('@playwright/test');

/**
 * Login helper — inicia sesión en el sistema
 * @param {Page} page - Página de Playwright
 * @param {Object} credentials - { username, password }
 */
async function login(page, { username, password }) {
  await page.goto('/login/');
  await page.fill('input[name="username"], #username, [data-test="username"]', username);
  await page.fill('input[name="password"], #password, [data-test="password"]', password);
  await page.click('button[type="submit"]');
  // Esperar a que la redirección ocurra después del login
  await page.waitForURL(/\/(dashboard|workspace|console|clientes)\/?/);
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
  const info = await page.evaluate(() => ({
    type: typeof window.http,
    version: window.http && window.http.__version__,
    hasGet: typeof window.http?.get,
    hasPost: typeof window.http?.post,
    hasPatch: typeof window.http?.patch,
    hasDelete: typeof window.http?.delete,
  }));

  expect(info.type).toBe('function');
  expect(info.version).toBe('3.4');
  expect(info.hasGet).toBe('function');
  expect(info.hasPost).toBe('function');
  expect(info.hasPatch).toBe('function');
  expect(info.hasDelete).toBe('function');
}

module.exports = { login, expectNoConsoleErrors, expectHttpAvailable };
