const { test, expect } = require('@playwright/test');

test('Edit Tenant funciona desde la consola pública', async ({ page }) => {
  const publicUrl = process.env.E2E_PUBLIC_URL || 'http://sintel.net.co:8000';
  const adminUser = process.env.E2E_ADMIN_USER || 'admin';
  const adminPass = process.env.E2E_ADMIN_PASS || 'admin';

  // Navegar a consola de tenants
  await page.goto(`${publicUrl}/console/tenants/`);
  await page.waitForLoadState('networkidle');

  // Login (si es necesario)
  const loginForm = page.locator('form').first();
  if (await loginForm.isVisible()) {
    await page.fill('[name="username"], #username', adminUser);
    await page.fill('[name="password"], #password', adminPass);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(console|admin)\/?/);
  }

  // Esperar que la tabla DataTables cargue
  await page.waitForSelector('#dt-tenants tbody tr', { timeout: 10000 });

  // Obtener la primera fila para editar
  const firstRow = page.locator('#dt-tenants tbody tr').first();
  await expect(firstRow).toBeVisible();

  // Hacer clic en el botón editar de la primera fila
  const editBtn = firstRow.locator('.btn-edit').first();
  await expect(editBtn).toBeVisible();
  await editBtn.click();

  // Esperar a que el modal se abra y esté en modo edit
  await page.waitForSelector('#tenant-form', { timeout: 5000 });

  // Generar nuevo nombre
  const newName = `Editado E2E ${Date.now()}`;

  // Rellenar el campo nombre
  const nombreField = page.locator('#nombre');
  await nombreField.fill(newName);

  // Verificar que los campos inmutables están readonly
  const schemaField = page.locator('#schema_name');
  const ownerField = page.locator('#owner_email');
  await expect(schemaField).toHaveAttribute('readonly', '');
  await expect(ownerField).toHaveAttribute('readonly', '');

  // Enviar formulario
  const submitBtn = page.locator('#tenant-form button[type="submit"]');
  await submitBtn.click();

  // Esperar a que se actualice la tabla (puede haber un pequeño delay)
  await page.waitForTimeout(1000);
  await page.reload();
  await page.waitForSelector('#dt-tenants tbody tr', { timeout: 10000 });

  // Verificar que el nombre fue actualizado
  await expect(page.locator(`#dt-tenants:has-text("${newName}")`)).toBeVisible({ timeout: 5000 });
});
