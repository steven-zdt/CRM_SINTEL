const { test, expect } = require('@playwright/test');
const { login, expectNoConsoleErrors } = require('./_helpers');

test('Contabilidad: crear → editar → eliminar cuenta', async ({ page }) => {
  const checkErrors = await expectNoConsoleErrors(page, 'contabilidad');
  const username = process.env.E2E_USER || 'test_user';
  const password = process.env.E2E_PASS || 'test_pass';

  // Login
  await login(page, { username, password });

  // Navegar a cuentas contables
  await page.goto('/contabilidad/cuentas/');
  await page.waitForLoadState('networkidle');

  // Verificar que la tabla existe
  const tableLocator = page.locator('[data-test="tabla-cuentas"], table').first();
  await expect(tableLocator).toBeVisible({ timeout: 5000 });

  // Generar timestamp único
  const ts = Date.now();
  const codigo = `9999${ts.toString().slice(-5)}`;
  const nombreCuenta = `Cuenta E2E ${ts}`;

  // **CREAR cuenta**
  const newBtn = page.locator('button:has-text("Nuevo"), button:has-text("Crear"), [data-test="btn-nueva-cuenta"]').first();
  await newBtn.click();

  // Llenar formulario
  const codigoInput = page.locator('[name="codigo"], #codigo').first();
  const nombreInput = page.locator('[name="nombre"], #nombre').first();
  const tipoSelect = page.locator('[name="tipo_cuenta"], #tipo_cuenta').first();

  await codigoInput.fill(codigo);
  await nombreInput.fill(nombreCuenta);

  // Seleccionar tipo de cuenta (usar index como fallback)
  try {
    await tipoSelect.selectOption('asset');
  } catch (_) {
    await tipoSelect.selectOption({ index: 1 });
  }

  // Guardar
  const saveBtn = page.locator('button:has-text("Guardar"), button:has-text("Crear")').first();
  await saveBtn.click();

  // Esperar a que aparezca en tabla
  await expect(page.locator(`text=${codigo}`)).toBeVisible({ timeout: 5000 });

  // **EDITAR cuenta**
  const nombreEditado = `${nombreCuenta} EDITED`;
  const editBtn = page.locator(`tr:has-text("${codigo}") .btn-edit, [data-test="edit-cuenta"]`).first();
  await editBtn.click();

  // Cambiar nombre
  const nombreInputEdit = page.locator('[name="nombre"], #nombre').first();
  await nombreInputEdit.fill(nombreEditado);

  const saveBtnEdit = page.locator('button:has-text("Guardar")').first();
  await saveBtnEdit.click();

  // Esperar confirmación
  await expect(page.locator(`text=${nombreEditado}`)).toBeVisible({ timeout: 5000 });

  // **ELIMINAR cuenta**
  page.once('dialog', (dialog) => dialog.accept());
  const deleteBtn = page.locator(`tr:has-text("${codigo}") .btn-delete, [data-test="delete-cuenta"]`).first();
  await deleteBtn.click();

  // Esperar a que desaparezca
  await expect(page.locator(`text=${codigo}`)).toBeHidden({ timeout: 5000 });

  // Verificar que no hay errores en consola
  checkErrors();
});
