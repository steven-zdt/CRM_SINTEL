const { test, expect } = require('@playwright/test');
const { login, expectHttpAvailable } = require('./_helpers');

test('window.http está disponible como función con métodos (v3.4)', async ({ page }) => {
  const username = process.env.E2E_USER || 'test_user';
  const password = process.env.E2E_PASS || 'test_pass';

  // Login
  await login(page, { username, password });

  // Navegar a dashboard del tenant
  await page.goto('/dashboard/');
  await page.waitForLoadState('networkidle');

  // Verificar que http.js v3.4 está cargado
  await expectHttpAvailable(page);

  // Verificación adicional: probar una llamada GET simple
  const result = await page.evaluate(async () => {
    try {
      const res = await window.http('GET', '/api/v1/clientes/?page_size=1');
      return {
        ok: res.ok,
        status: res.status,
        hasData: !!res.data,
      };
    } catch (err) {
      return {
        error: err.message,
      };
    }
  });

  expect(result.error).toBeUndefined();
  expect(result.ok).toBe(true);
  expect(result.status).toBe(200);
  expect(result.hasData).toBe(true);
});
