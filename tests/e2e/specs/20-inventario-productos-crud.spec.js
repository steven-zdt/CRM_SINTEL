const { test, expect } = require('@playwright/test');
const { login, expectNoConsoleErrors } = require('./_helpers');

test('Inventario: crear → editar → eliminar producto', async ({ page }) => {
  const username = process.env.E2E_USER || 'test_user';
  const password = process.env.E2E_PASS || 'test_pass';

  // Login
  await login(page, { username, password });

  // F32.5: Inventario es un TAB dentro de /workspace/ (hash routing), no una
  // pagina propia -- mismo patron que Clientes (ver 10-clientes-crud.spec.js).
  // /inventario/ no es la UI real.
  await page.goto('/workspace/#inventario');
  await page.waitForSelector('#tab-inventario', { state: 'visible', timeout: 10000 });

  // Listener de errores instalado DESPUES de aterrizar en el tab, para no
  // capturar el 404 real y preexistente del tab Dashboard (ver commit
  // "F32.5 -- corregir spec E2E de Clientes", flageado en task_8c73f54c).
  const checkErrors = await expectNoConsoleErrors(page, 'inventario');

  // Panel HTMX real: #productos-panel (apps/tenant/inventario/templates/
  // tenant/inventario/list_productos.html) -- el sub-tab de Productos puede
  // no estar activo por defecto dentro de Inventario, verificar si hace
  // falta un click adicional.
  const productosTab = page.locator('[data-bs-target="#tab-pane-productos"], a:has-text("Productos"), button:has-text("Productos")').first();
  if (await productosTab.count() > 0) {
    await productosTab.click().catch(() => {});
  }

  const tableLocator = page.locator('#productos-panel table, #tabla-productos').first();
  await expect(tableLocator).toBeVisible({ timeout: 10000 });

  // Generar timestamp único
  const ts = Date.now();
  const sku = `E2E-${ts.toString().slice(-8)}`;
  const productName = `Producto E2E ${ts}`;

  // **CREAR producto** -- boton real: #btn-nuevo-producto (list_productos.html:27)
  await page.click('#btn-nuevo-producto');

  // Offcanvas real: offcanvas_producto.html -- campos verificados contra el
  // markup fuente (no hay campo tipo_producto -- suposicion incorrecta del
  // spec original).
  await page.waitForSelector('#offcanvas-inventario.show', { timeout: 5000 });
  await page.fill('#producto-codigo', sku);
  await page.fill('#producto-nombre', productName);
  await page.fill('#producto-unidad', 'UND');
  await page.fill('#producto-precio-venta', '10000');
  await page.fill('#producto-stock-minimo', '1');

  await page.click('#btn-guardar-producto');

  await expect(page.locator(`#productos-panel:has-text("${productName}")`)).toBeVisible({ timeout: 10000 });

  // **EDITAR producto** -- boton real: .btn-edit-producto data-uuid
  // (apps/tenant/inventario/tables.py:131)
  const editBtn = page.locator(`#productos-panel tr:has-text("${productName}") .btn-edit-producto`).first();
  await editBtn.click();

  const editedName = `${productName} EDITED`;
  await page.waitForSelector('#offcanvas-inventario.show', { timeout: 5000 });
  await page.fill('#producto-nombre', editedName);
  // Regla de negocio real (productos_list.js:183-184): no se puede eliminar
  // un producto activo -- hay que desactivarlo primero.
  await page.uncheck('#producto-activo');
  await page.click('#btn-guardar-producto');

  await expect(page.locator(`#productos-panel:has-text("${editedName}")`)).toBeVisible({ timeout: 10000 });

  // **ELIMINAR producto** -- boton real: .btn-delete-producto data-uuid
  page.once('dialog', (dialog) => dialog.accept());
  const deleteBtn = page.locator(`#productos-panel tr:has-text("${editedName}") .btn-delete-producto`).first();
  await deleteBtn.click();

  await expect(page.locator(`#productos-panel:has-text("${editedName}")`)).toBeHidden({ timeout: 10000 });

  // Verificar que no hay errores en consola
  checkErrors();
});
