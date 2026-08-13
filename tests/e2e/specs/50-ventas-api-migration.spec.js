const { test, expect } = require('@playwright/test');
const { login } = require('./_helpers');

// F32.6: verifica que ventas.api.js migrado a Sintel.Core.Http sigue
// funcionando -- mismo contrato publico (Sintel.Ventas.API.list() lanza
// en error, retorna datos en exito), transporte interno cambiado.
test('F32.6: ventas.api.js migrado a Core.Http funciona (list, resoluciones.list)', async ({ page }) => {
  const username = process.env.E2E_USER || 'test_user';
  const password = process.env.E2E_PASS || 'test_pass';

  await login(page, { username, password });
  await page.goto('/workspace/#ventas');
  await page.waitForSelector('#tab-ventas', { state: 'visible', timeout: 10000 });

  const result = await page.evaluate(async () => {
    try {
      const ventas = await window.Sintel.Ventas.API.list({ page_size: 1 });
      const resoluciones = await window.Sintel.Ventas.API.resoluciones.list({ page_size: 1 });
      return {
        hasVentas: !!ventas,
        ventasHasResults: Array.isArray(ventas?.results) || Array.isArray(ventas),
        hasResoluciones: !!resoluciones,
      };
    } catch (err) {
      return { error: err.message, status: err.status, data: err.data };
    }
  });

  expect(result.error).toBeUndefined();
  expect(result.hasVentas).toBe(true);
  expect(result.ventasHasResults).toBe(true);
  expect(result.hasResoluciones).toBe(true);
});
