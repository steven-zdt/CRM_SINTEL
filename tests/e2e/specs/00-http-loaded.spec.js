const { test, expect } = require('@playwright/test');
const { login } = require('./_helpers');

// F32.7: client A (core/js/lib/http.js, window.http/window.getCookie) fue
// removido tras confirmar y migrar sus 52 consumidores reales (F32.6: 6
// archivos que reimplementaban fetch por su cuenta; F32.7: 46 mas que
// delegaban correctamente pero seguian atados al transporte viejo). Este
// spec ahora confirma la remocion (window.http ya no existe en ningun
// contexto real) en vez de su presencia -- ver
// F32_7_TRANSPORT_CONSOLIDATION_AUDIT.md.
test('F32.7: window.http (client A) fue removido -- Sintel.Core.Http es el unico transporte', async ({ page }) => {
  const username = process.env.E2E_USER || 'test_user';
  const password = process.env.E2E_PASS || 'test_pass';

  await login(page, { username, password });
  await page.goto('/workspace/#dashboard');
  await page.waitForSelector('#tab-dashboard', { state: 'visible', timeout: 10000 });

  const result = await page.evaluate(async () => {
    const shape = {
      httpType: typeof window.http,
      getCookieType: typeof window.getCookie,
      coreHttpType: typeof window.Sintel?.Core?.Http,
    };
    try {
      const res = await window.Sintel.Core.Http.get('/api/v1/clientes/?page_size=1');
      return { ...shape, ok: res.ok, status: res.status, hasData: !!res.data };
    } catch (err) {
      return { ...shape, error: err.message };
    }
  });

  expect(result.httpType).toBe('undefined');
  expect(result.getCookieType).toBe('undefined');
  expect(result.coreHttpType).toBe('object');
  expect(result.error).toBeUndefined();
  expect(result.ok).toBe(true);
  expect(result.status).toBe(200);
  expect(result.hasData).toBe(true);
});

test('F32.7: Sintel.Core.Http esta disponible y funciona (unico transporte, ya no aditivo)', async ({ page }) => {
  const username = process.env.E2E_USER || 'test_user';
  const password = process.env.E2E_PASS || 'test_pass';

  await login(page, { username, password });
  // F32.6/F32.7: /dashboard/ es un RedirectView a un shell HTML ESTATICO
  // (static/tenant/core/dashboard/index.html, config/urls_tenant.py:140)
  // que NUNCA incluyo assets_core.html (un 6o punto de carga independiente,
  // ya roto por separado -- ver F32_7_TRANSPORT_CONSOLIDATION_AUDIT.md).
  // core-http.js solo se carga via assets_core.html, incluido en
  // /workspace/.
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
