const { test, expect } = require('@playwright/test');
const { login } = require('./_helpers');

// F32.6: verifica que empleados.api.js migrado a Sintel.Core.Http sigue
// funcionando -- request(url, options) mantiene su forma de retorno
// {ok,status,data} identica (el unico consumidor real es
// contrato_list.js:38, que llama request(url, {method:'POST'}) sin body).
test('F32.6: empleados.api.js migrado a Core.Http funciona (request GET)', async ({ page }) => {
  const username = process.env.E2E_USER || 'test_user';
  const password = process.env.E2E_PASS || 'test_pass';

  await login(page, { username, password });
  await page.goto('/workspace/#empleados');
  await page.waitForSelector('#tab-empleados', { state: 'visible', timeout: 10000 });

  const result = await page.evaluate(async () => {
    const API = window.Sintel.Empleados.API;
    const shape = {
      hasList: typeof API?.empleados?.list,
      hasCancelarUrl: typeof API?.contratos?.cancelar,
      hasRequest: typeof window.Sintel.Empleados.request,
    };
    try {
      const res = await window.Sintel.Empleados.request(API.empleados.list);
      return { ...shape, ok: res.ok, status: res.status, hasData: !!res.data };
    } catch (err) {
      return { ...shape, error: err.message };
    }
  });

  expect(result.hasList).toBe('string');
  expect(result.hasCancelarUrl).toBe('function');
  expect(result.hasRequest).toBe('function');
  expect(result.error).toBeUndefined();
  expect(result.ok).toBe(true);
  expect(result.status).toBe(200);
  expect(result.hasData).toBe(true);
});
