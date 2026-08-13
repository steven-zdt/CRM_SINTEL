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

test('F32.6: Sintel.Core.Http esta disponible y funciona (aditivo, no reemplaza window.http)', async ({ page }) => {
  const username = process.env.E2E_USER || 'test_user';
  const password = process.env.E2E_PASS || 'test_pass';

  await login(page, { username, password });
  // F32.6: /dashboard/ es un RedirectView a un shell HTML ESTATICO
  // (static/tenant/core/dashboard/index.html, config/urls_tenant.py:140)
  // que carga lib/http.js con su propio <script> hardcodeado -- NUNCA
  // incluye assets_core.html (un 6o punto de carga independiente,
  // hallazgo F32.6 -- ver F32_1_2_TRANSPORT_AUDIT.md). core-http.js solo
  // se agrega a assets_core.html, que si se incluye en /workspace/.
  await page.goto('/workspace/#dashboard');
  await page.waitForSelector('#tab-dashboard', { state: 'visible', timeout: 10000 });

  const result = await page.evaluate(async () => {
    const shape = {
      type: typeof window.Sintel?.Core?.Http,
      hasGet: typeof window.Sintel?.Core?.Http?.get,
      hasPost: typeof window.Sintel?.Core?.Http?.post,
      hasUpload: typeof window.Sintel?.Core?.Http?.upload,
      hasCsrf: typeof window.Sintel?.Core?.Http?.csrf,
    };
    try {
      const res = await window.Sintel.Core.Http.get('/api/v1/clientes/?page_size=1');
      return { ...shape, ok: res.ok, status: res.status, hasData: !!res.data };
    } catch (err) {
      return { ...shape, error: err.message };
    }
  });

  expect(result.type).toBe('object');
  expect(result.hasGet).toBe('function');
  expect(result.hasPost).toBe('function');
  expect(result.hasUpload).toBe('function');
  expect(result.hasCsrf).toBe('function');
  expect(result.error).toBeUndefined();
  expect(result.ok).toBe(true);
  expect(result.status).toBe(200);
  expect(result.hasData).toBe(true);
});
