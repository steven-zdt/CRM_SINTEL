const { test, expect } = require('@playwright/test');
const { login } = require('./_helpers');

// F32.6: verifica que dashboard.api.js migrado a Sintel.Core.Http sigue
// funcionando -- obtenerMetricas()/invalidarCache()/obtenerKpisPorSede()
// delegan en Core.Http.request() pero conservan su contrato publico
// original (Promise que resuelve con datos o lanza Error). El unico
// consumidor externo real es dashboard_main.js:39 (obtenerMetricas(), sin
// inspeccionar .status/.data del error -- solo error.message via
// console.error generico).
test('F32.6: dashboard.api.js migrado a Core.Http funciona (obtenerMetricas)', async ({ page }) => {
  const username = process.env.E2E_USER || 'test_user';
  const password = process.env.E2E_PASS || 'test_pass';

  await login(page, { username, password });
  await page.goto('/workspace/#dashboard');
  await page.waitForSelector('#tab-dashboard', { state: 'visible', timeout: 10000 });

  const result = await page.evaluate(async () => {
    const shape = {
      hasObtenerMetricas: typeof window.Sintel.Dashboard?.obtenerMetricas,
      hasInvalidarCache: typeof window.Sintel.Dashboard?.invalidarCache,
      hasObtenerKpisPorSede: typeof window.Sintel.Dashboard?.obtenerKpisPorSede,
    };
    try {
      const data = await window.Sintel.Dashboard.obtenerMetricas();
      return { ...shape, hasData: !!data };
    } catch (err) {
      return { ...shape, error: err.message };
    }
  });

  expect(result.hasObtenerMetricas).toBe('function');
  expect(result.hasInvalidarCache).toBe('function');
  expect(result.hasObtenerKpisPorSede).toBe('function');
  expect(result.error).toBeUndefined();
  expect(result.hasData).toBe(true);
});
