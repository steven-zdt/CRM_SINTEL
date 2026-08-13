const { test, expect } = require('@playwright/test');
const { login } = require('./_helpers');

// F32.7: dos consumidores inline de window.http (client A) hallados fuera de
// los *.api.js -- ninguno pasaba por un wrapper SSoT, cada uno llamaba
// window.http() directo dentro de su feature. Migrados a
// Sintel.Core.Http.request(). Ver F32_7_TRANSPORT_CONSOLIDATION_AUDIT.md.

test('F32.7: empleado_list.js loadSummary() migrado a Core.Http funciona', async ({ page }) => {
  const username = process.env.E2E_USER || 'test_user';
  const password = process.env.E2E_PASS || 'test_pass';

  await login(page, { username, password });
  await page.goto('/workspace/#empleados');
  await page.waitForSelector('#tab-empleados', { state: 'visible', timeout: 10000 });

  const result = await page.evaluate(async () => {
    // El panel resumen no esta necesariamente en el DOM montado (subtab) --
    // se prueba loadSummary() directo contra el elemento real si existe,
    // o se crea uno temporal si el subtab de resumen no esta activo.
    let el = document.getElementById('panel-resumen-empleados');
    let created = false;
    if (!el) {
      el = document.createElement('div');
      el.id = 'panel-resumen-empleados';
      el.style.display = 'none';
      document.body.appendChild(el);
      created = true;
    }
    try {
      await window.Sintel.Empleados.EmpleadoList.loadSummary('#panel-resumen-empleados');
      return { ok: true, hasTotalEmpleados: !!document.getElementById('total-empleados') };
    } catch (err) {
      return { ok: false, error: err.message };
    } finally {
      if (created) el.remove();
    }
  });

  expect(result.error).toBeUndefined();
  expect(result.ok).toBe(true);
});

test('F32.7: representante_editor.js busqueda tipeada migrada a Core.Http funciona', async ({ page }) => {
  const username = process.env.E2E_USER || 'test_user';
  const password = process.env.E2E_PASS || 'test_pass';

  await login(page, { username, password });
  await page.goto('/workspace/#proveedores');
  await page.waitForSelector('#tab-proveedores', { state: 'visible', timeout: 10000 });

  // representante_editor.js no expone su busqueda en un namespace global --
  // se prueba el mismo endpoint con el mismo transporte (Core.Http) para
  // confirmar que /api/v1/proveedores/?search=... sigue respondiendo 200
  // via el cliente unico.
  const result = await page.evaluate(async () => {
    const res = await window.Sintel.Core.Http.request(
      'GET',
      '/api/v1/proveedores/?search=a&page_size=15&activo=true'
    );
    return { ok: res.ok, status: res.status, hasResults: Array.isArray(res.data?.results) };
  });

  expect(result.ok).toBe(true);
  expect(result.status).toBe(200);
  expect(result.hasResults).toBe(true);
});
