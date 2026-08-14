const { test, expect } = require('@playwright/test');
const { login } = require('./_helpers');

// F32.9.5: hallazgo real de la revalidacion de gobernanza -- reporte.api.js
// (contabilidad) nunca fue tocado por F32.6/F32.7 (esas fases solo
// auditaron window.http/w.http, no fetch() directo). Reimplementaba su
// propio fetch+JWT manual sin refresh (mismo patron de bug documentado en
// F32.1 para los 6 archivos originales). Migrado a Sintel.Core.Http.
test('F32.9: reporte.api.js migrado a Core.Http funciona (Balance de Prueba + Estado de Resultados)', async ({ page }) => {
  const username = process.env.E2E_USER || 'test_user';
  const password = process.env.E2E_PASS || 'test_pass';

  await login(page, { username, password });
  await page.goto('/workspace/#contabilidad');
  await page.waitForSelector('#tab-contabilidad', { state: 'visible', timeout: 10000 });

  const result = await page.evaluate(async () => {
    const api = window.Sintel.Contabilidad.ReporteAPI;
    const shape = {
      hasBalance: typeof api?.getBalancePrueba,
      hasEstado: typeof api?.getEstadoResultados,
    };
    try {
      const [balance, estado] = await Promise.all([
        api.getBalancePrueba('2026-01-01', '2026-12-31'),
        api.getEstadoResultados('2026-01-01', '2026-12-31'),
      ]);
      return { ...shape, hasBalanceData: balance !== undefined, hasEstadoData: estado !== undefined };
    } catch (err) {
      return { ...shape, error: err.message };
    }
  });

  expect(result.hasBalance).toBe('function');
  expect(result.hasEstado).toBe('function');
  expect(result.error).toBeUndefined();
  expect(result.hasBalanceData).toBe(true);
  expect(result.hasEstadoData).toBe(true);
});
