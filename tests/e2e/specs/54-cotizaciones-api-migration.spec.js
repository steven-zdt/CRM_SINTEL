const { test, expect } = require('@playwright/test');
const { login } = require('./_helpers');

// F32.6: verifica que cotizaciones.api.js migrado a Sintel.Core.Http sigue
// funcionando. Este archivo no expone list() como funcion (solo URLs de
// string), asi que se prueba con Core.Http.get() directo contra las URLs
// publicadas, mas la disponibilidad de los metodos de Configuracion.
test('F32.6: cotizaciones.api.js migrado a Core.Http funciona (URLs + metodos)', async ({ page }) => {
  const username = process.env.E2E_USER || 'test_user';
  const password = process.env.E2E_PASS || 'test_pass';

  await login(page, { username, password });
  await page.goto('/workspace/#cotizaciones');
  await page.waitForSelector('#tab-cotizaciones', { state: 'visible', timeout: 10000 });

  const result = await page.evaluate(async () => {
    const api = window.Sintel.Cotizaciones.api;
    const shape = {
      hasCreateConfig: typeof api?.createConfiguracion,
      hasUpdateConfig: typeof api?.updateConfiguracion,
      hasDeleteConfig: typeof api?.deleteConfiguracion,
    };
    try {
      const res = await window.Sintel.Core.Http.get(api.listUrl);
      const config = await window.Sintel.Core.Http.get(api.configuracionUrl);
      return {
        ...shape,
        ok: res.ok,
        status: res.status,
        hasData: !!res.data,
        configOk: config.ok,
        configStatus: config.status,
      };
    } catch (err) {
      return { ...shape, error: err.message || JSON.stringify(err) };
    }
  });

  expect(result.hasCreateConfig).toBe('function');
  expect(result.hasUpdateConfig).toBe('function');
  expect(result.hasDeleteConfig).toBe('function');
  expect(result.error).toBeUndefined();
  expect(result.ok).toBe(true);
  expect(result.status).toBe(200);
  expect(result.hasData).toBe(true);
  expect(result.configOk).toBe(true);
  expect(result.configStatus).toBe(200);
});
