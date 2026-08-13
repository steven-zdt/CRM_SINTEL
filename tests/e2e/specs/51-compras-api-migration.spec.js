const { test, expect } = require('@playwright/test');
const { login } = require('./_helpers');

// F32.6: verifica que compras.api.js migrado a Sintel.Core.Http sigue
// funcionando -- mismo contrato publico (lanza Error con .status/.data
// en fallo), transporte interno cambiado.
test('F32.6: compras.api.js migrado a Core.Http funciona (list)', async ({ page }) => {
  const username = process.env.E2E_USER || 'test_user';
  const password = process.env.E2E_PASS || 'test_pass';

  await login(page, { username, password });
  await page.goto('/workspace/#compras');
  await page.waitForSelector('#tab-compras', { state: 'visible', timeout: 10000 });

  const result = await page.evaluate(async () => {
    const API = window.Sintel.Compras.API;
    const shape = {
      hasCreate: typeof API?.compras?.create,
      hasUpdate: typeof API?.compras?.update,
      hasCambiarEstado: typeof API?.cambiarEstado,
      hasEliminar: typeof API?.eliminar,
    };
    try {
      const res = await window.Sintel.Core.Http.get(API.compras.list);
      const plantillas = await window.Sintel.Core.Http.get(API.plantillas.list);
      return { ...shape, ok: res.ok, status: res.status, hasData: !!res.data, plantillasOk: plantillas.ok };
    } catch (err) {
      return { ...shape, error: err.message, status: err.status, data: err.data };
    }
  });

  expect(result.hasCreate).toBe('function');
  expect(result.hasUpdate).toBe('function');
  expect(result.hasCambiarEstado).toBe('function');
  expect(result.hasEliminar).toBe('function');
  expect(result.error).toBeUndefined();
  expect(result.ok).toBe(true);
  expect(result.status).toBe(200);
  expect(result.hasData).toBe(true);
  expect(result.plantillasOk).toBe(true);
});
