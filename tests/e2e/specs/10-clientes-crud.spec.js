const { test, expect } = require('@playwright/test');
const { login, expectNoConsoleErrors } = require('./_helpers');

test('Clientes: crear → editar → eliminar', async ({ page }) => {
  const checkErrors = await expectNoConsoleErrors(page, 'clientes');
  const username = process.env.E2E_USER || 'test_user';
  const password = process.env.E2E_PASS || 'test_pass';

  // Login
  await login(page, { username, password });

  // Navegar a clientes
  await page.goto('/clientes/');
  await page.waitForLoadState('networkidle');

  // Verificar que la tabla existe
  const tableLocator = page.locator('#tabla-clientes, [data-test="tabla-clientes"], table').first();
  await expect(tableLocator).toBeVisible({ timeout: 5000 });

  // Generar timestamp único para el cliente
  const ts = Date.now();
  const clientName = `E2E Test ${ts}`;
  const nit = `9001${ts.toString().slice(-6)}`;

  // **CREAR cliente**
  const newBtn = page.locator('button:has-text("Nuevo"), button:has-text("Crear"), [data-test="btn-nuevo-cliente"]').first();
  await newBtn.click();

  // Llenar formulario (selectores tolerantes)
  const typeSelect = page.locator('#cliente-tipo_persona, [name="tipo_persona"]').first();
  const docTypeSelect = page.locator('#cliente-tipo_documento, [name="tipo_documento"]').first();
  const nitInput = page.locator('#cliente-numero_documento, [name="numero_documento"]').first();
  const nameInput = page.locator('#cliente-razon_social, [name="razon_social"]').first();
  const regimeSelect = page.locator('#cliente-regimen_tributario, [name="regimen_tributario"]').first();

  await typeSelect.selectOption('PJ');
  await docTypeSelect.selectOption('NIT');
  await nitInput.fill(nit);
  await nameInput.fill(clientName);
  await regimeSelect.selectOption({ index: 1 });

  // Guardar
  const saveBtn = page.locator('#btn-guardar-cliente, button:has-text("Guardar")').first();
  await saveBtn.click();

  // Esperar a que aparezca en la tabla
  await expect(page.locator(`text=${clientName}`)).toBeVisible({ timeout: 5000 });

  // **EDITAR cliente**
  const editedName = `${clientName} EDITED`;
  const editBtn = page.locator(`tr:has-text("${clientName}") .btn-edit, [data-test="edit-cliente"]`).first();
  await editBtn.click();

  // Cambiar razón social
  const nameInputEdit = page.locator('#cliente-razon_social, [name="razon_social"]').first();
  await nameInputEdit.fill(editedName);

  const saveBtnEdit = page.locator('#btn-guardar-cliente, button:has-text("Guardar")').first();
  await saveBtnEdit.click();

  // Esperar confirmación
  await expect(page.locator(`text=${editedName}`)).toBeVisible({ timeout: 5000 });

  // **ELIMINAR cliente**
  page.once('dialog', (dialog) => dialog.accept());
  const deleteBtn = page.locator(`tr:has-text("${editedName}") .btn-delete, [data-test="delete-cliente"]`).first();
  await deleteBtn.click();

  // Esperar a que desaparezca
  await expect(page.locator(`text=${editedName}`)).toBeHidden({ timeout: 5000 });

  // Verificar que no hay errores en consola
  checkErrors();
});
