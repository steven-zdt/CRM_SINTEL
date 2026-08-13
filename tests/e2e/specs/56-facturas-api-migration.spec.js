const { test, expect } = require('@playwright/test');
const { login } = require('./_helpers');

// F32.7: verifica que facturas.api.js migrado de window.http (client A,
// lib/http.js) a Sintel.Core.Http sigue funcionando. Este archivo no fue
// parte de los "6 no conformes" de F32.6 (no reimplementaba fetch+CSRF+JWT,
// ya delegaba correctamente en window.http) pero SI dependia duro de ese
// transporte (guard clause que abortaba todo el IIFE si window.http no
// existia) -- hallazgo nuevo de la auditoria F32.7, ver
// F32_7_TRANSPORT_CONSOLIDATION_AUDIT.md.
test('F32.7: facturas.api.js migrado a Core.Http funciona (listFacturas + getSummary)', async ({ page }) => {
  const username = process.env.E2E_USER || 'test_user';
  const password = process.env.E2E_PASS || 'test_pass';

  await login(page, { username, password });
  await page.goto('/workspace/#facturas');
  await page.waitForSelector('#tab-facturas', { state: 'visible', timeout: 10000 });

  const result = await page.evaluate(async () => {
    const api = window.facturasAPI;
    const shape = {
      hasApi: !!api,
      hasListFacturas: typeof api?.listFacturas,
      hasUploadDocumento: typeof api?.uploadDocumento,
      hasGetDocumentXML: typeof api?.getDocumentXML,
    };
    try {
      const listRes = await api.listFacturas();
      const summaryRes = await api.getSummary();
      return {
        ...shape,
        listOk: listRes.ok,
        listStatus: listRes.status,
        summaryOk: summaryRes.ok,
        summaryStatus: summaryRes.status,
      };
    } catch (err) {
      return { ...shape, error: err.message };
    }
  });

  expect(result.hasApi).toBe(true);
  expect(result.hasListFacturas).toBe('function');
  expect(result.hasUploadDocumento).toBe('function');
  expect(result.hasGetDocumentXML).toBe('function');
  expect(result.error).toBeUndefined();
  expect(result.listOk).toBe(true);
  expect(result.listStatus).toBe(200);
  expect(result.summaryOk).toBe(true);
  expect(result.summaryStatus).toBe(200);
});
