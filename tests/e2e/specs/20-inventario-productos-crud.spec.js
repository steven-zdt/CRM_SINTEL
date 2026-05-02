const { test, expect } = require('@playwright/test');
const { login, expectNoConsoleErrors } = require('./_helpers');

test('Inventario: crear → editar → eliminar producto', async ({ page }) => {
  const checkErrors = await expectNoConsoleErrors(page, 'inventario');
  const username = process.env.E2E_USER || 'test_user';
  const password = process.env.E2E_PASS || 'test_pass';

  // Login
  await login(page, { username, password });

  // Navegar a inventario
  await page.goto('/inventario/');
  await page.waitForLoadState('networkidle');

  // Verificar que la tabla existe
  const tableLocator = page.locator('[data-test="tabla-productos"], table').first();
  await expect(tableLocator).toBeVisible({ timeout: 5000 });

  // Generar timestamp único
  const ts = Date.now();
  const sku = `E2E-${ts.toString().slice(-8)}`;
  const productName = `Producto E2E ${ts}`;

  // **CREAR producto**
  const newBtn = page.locator('button:has-text("Nuevo"), button:has-text("Crear"), [data-test="btn-nuevo-producto"]').first();
  await newBtn.click();

  // Llenar formulario (selectores tolerantes)
  const skuInput = page.locator('[name="codigo"], [name="sku"], #sku').first();
  const nameInput = page.locator('[name="nombre"], #nombre').first();
  const typeSelect = page.locator('[name="tipo_producto"], #tipo_producto').first();

  await skuInput.fill(sku);
  await nameInput.fill(productName);
  // Seleccionar el tipo de producto (puede variar, usar index como fallback)
  try {
    await typeSelect.selectOption('product');
  } catch (_) {
    await typeSelect.selectOption({ index: 1 });
  }

  // Guardar
  const saveBtn = page.locator('button:has-text("Guardar")').first();
  await saveBtn.click();

  // Esperar a que aparezca en tabla
  await expect(page.locator(`text=${sku}`)).toBeVisible({ timeout: 5000 });

  // **EDITAR producto**
  const editedName = `${productName} EDITED`;
  const editBtn = page.locator(`tr:has-text("${sku}") .btn-edit, [data-test="edit-producto"]`).first();
  await editBtn.click();

  // Cambiar nombre
  const nameInputEdit = page.locator('[name="nombre"], #nombre').first();
  await nameInputEdit.fill(editedName);

  const saveBtnEdit = page.locator('button:has-text("Guardar")').first();
  await saveBtnEdit.click();

  // Esperar confirmación
  await expect(page.locator(`text=${editedName}`)).toBeVisible({ timeout: 5000 });

  // **ELIMINAR producto**
  page.once('dialog', (dialog) => dialog.accept());
  const deleteBtn = page.locator(`tr:has-text("${sku}") .btn-delete, [data-test="delete-producto"]`).first();
  await deleteBtn.click();

  // Esperar a que desaparezca
  await expect(page.locator(`text=${sku}`)).toBeHidden({ timeout: 5000 });

  // Verificar que no hay errores en consola
  checkErrors();
});
