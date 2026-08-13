const { test, expect } = require('@playwright/test');
const { login } = require('./_helpers');

// F32.6: verifica que gastos.api.js migrado a Sintel.Core.Http sigue
// funcionando -- mismo contrato publico, transporte interno cambiado.
test('F32.6: gastos.api.js migrado a Core.Http funciona (list, resoluciones)', async ({ page }) => {
  const username = process.env.E2E_USER || 'test_user';
  const password = process.env.E2E_PASS || 'test_pass';

  await login(page, { username, password });
  await page.goto('/workspace/#gastos');
  await page.waitForSelector('#tab-gastos', { state: 'visible', timeout: 10000 });

  const result = await page.evaluate(async () => {
    const API = window.Sintel.Gastos.API;
    const shape = {
      hasCreate: typeof API?.gastos?.create,
      hasUpdate: typeof API?.gastos?.update,
      hasAnular: typeof API?.anular,
      hasEliminar: typeof API?.eliminar,
    };
    try {
      const res = await window.Sintel.Core.Http.get(API.gastos.list);
      const resoluciones = await window.Sintel.Core.Http.get(API.resoluciones.list);
      return { ...shape, ok: res.ok, status: res.status, hasData: !!res.data, resolucionesOk: resoluciones.ok };
    } catch (err) {
      return { ...shape, error: err.message, status: err.status, data: err.data };
    }
  });

  expect(result.hasCreate).toBe('function');
  expect(result.hasUpdate).toBe('function');
  expect(result.hasAnular).toBe('function');
  expect(result.hasEliminar).toBe('function');
  expect(result.error).toBeUndefined();
  expect(result.ok).toBe(true);
  expect(result.status).toBe(200);
  expect(result.hasData).toBe(true);
  expect(result.resolucionesOk).toBe(true);
});
