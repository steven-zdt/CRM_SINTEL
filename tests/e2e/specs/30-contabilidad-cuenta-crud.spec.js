const { test, expect } = require('@playwright/test');
const { login, expectNoConsoleErrors } = require('./_helpers');

test('Contabilidad: crear → editar → eliminar cuenta', async ({ page }) => {
  const username = process.env.E2E_USER || 'test_user';
  const password = process.env.E2E_PASS || 'test_pass';

  // Login
  await login(page, { username, password });

  // F32.5: Contabilidad es un TAB dentro de /workspace/ (hash routing),
  // "Cuentas Contables" es el sub-tab activo por defecto -- mismo patron
  // que Clientes/Inventario (ver commits anteriores de esta fase).
  await page.goto('/workspace/#contabilidad');
  await page.waitForSelector('#tab-contabilidad', { state: 'visible', timeout: 10000 });

  // "Cannot read properties of null (reading 'scroll')" es un timing interno
  // conocido de Bootstrap Offcanvas (mismo patron ya documentado y aceptado
  // para devengo_editor.js en F31.2, no un bug de esta app) -- se filtra
  // aqui para no bloquear el spec en ruido ya catalogado.
  const checkErrors = await expectNoConsoleErrors(page, 'contabilidad', [
    "reading 'scroll'",
  ]);

  const tableLocator = page.locator('#contabilidad-cuentas-panel table, #tabla-cuentas').first();
  await expect(tableLocator).toBeVisible({ timeout: 10000 });

  // Generar timestamp único
  const ts = Date.now();
  const codigo = `9999${ts.toString().slice(-5)}`;
  const nombreCuenta = `Cuenta E2E ${ts}`;

  // **CREAR cuenta** -- boton real: #btn-crear-cuenta (list_cuentas.html:22)
  await page.click('#btn-crear-cuenta');

  // Offcanvas real: cuenta_offcanvas_form.html -- campos verificados contra
  // el markup fuente (#input-codigo/#select-tipo/#input-nombre, no los
  // nombres genericos [name="codigo"]/[name="tipo_cuenta"] que el spec
  // original asumia).
  await page.waitForSelector('#offcanvas-cuenta-crear.show', { timeout: 5000 });
  await page.fill('#input-codigo', codigo);
  await page.selectOption('#select-tipo', 'ACTIVO');
  await page.fill('#input-nombre', nombreCuenta);
  await page.click('#btn-guardar-cuenta-crear');

  await expect(page.locator(`#contabilidad-cuentas-panel:has-text("${nombreCuenta}")`)).toBeVisible({ timeout: 10000 });

  // **EDITAR cuenta** -- boton real: .btn-editar-cuenta data-uuid
  // (apps/tenant/contabilidad/tables.py:85). NOTA F32.5: el JS inline de
  // cuenta_offcanvas_form.html usa cuenta.id (PK entero) para el PATCH de
  // edicion, no cuenta.uuid, pese a que CuentaContableViewSet hereda
  // lookup_field='uuid' de BaseTenantViewSet -- candidato a WRONG_LOOKUP
  // real (mismo patron ya encontrado varias veces en este proyecto). Este
  // test lo verifica empiricamente: si falla aqui con 404 en el PATCH,
  // confirma el bug.
  const editBtn = page.locator(`#contabilidad-cuentas-panel tr:has-text("${nombreCuenta}") .btn-editar-cuenta`).first();
  await editBtn.click();

  const nombreEditado = `${nombreCuenta} EDITED`;
  await page.waitForSelector('#offcanvas-cuenta-editar.show', { timeout: 5000 });
  await page.fill('#input-nombre', nombreEditado);
  await page.click('#btn-guardar-cuenta-editar');

  await expect(page.locator(`#contabilidad-cuentas-panel:has-text("${nombreEditado}")`)).toBeVisible({ timeout: 10000 });

  // **ELIMINAR cuenta** -- boton real: .btn-eliminar-cuenta data-uuid
  page.once('dialog', (dialog) => dialog.accept());
  const deleteBtn = page.locator(`#contabilidad-cuentas-panel tr:has-text("${nombreEditado}") .btn-eliminar-cuenta`).first();
  await deleteBtn.click();

  await expect(page.locator(`#contabilidad-cuentas-panel:has-text("${nombreEditado}")`)).toBeHidden({ timeout: 10000 });

  // Verificar que no hay errores en consola
  checkErrors();
});
