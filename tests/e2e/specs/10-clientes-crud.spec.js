const { test, expect } = require('@playwright/test');
const { login, expectNoConsoleErrors } = require('./_helpers');

test('Clientes: crear → editar → eliminar', async ({ page }) => {
  const username = process.env.E2E_USER || 'test_user';
  const password = process.env.E2E_PASS || 'test_pass';

  // Login
  await login(page, { username, password });

  // F32.5: corregido contra el markup real (verificado leyendo el codigo
  // fuente, no supuesto). Clientes es un TAB dentro de /workspace/ (hash
  // routing, no una pagina propia) -- ver
  // apps/tenant/core/templates/tenant/core/workspace.html:49/95.
  // /clientes/ y /ui/clientes/ NO son la UI (el segundo es el endpoint
  // DRF crudo, confirmado con 404/JSON reales en un pase anterior).
  await page.goto('/workspace/#clientes');
  await page.waitForSelector('#tab-clientes', { state: 'visible', timeout: 10000 });

  // El listener de errores se instala DESPUES de aterrizar en el tab
  // Dashboard (default de /workspace/) y navegar a Clientes -- el tab
  // Dashboard tiene un 404 real y preexistente en 3 assets estaticos
  // (/static/core/js/dashboard/dashboard.{api,ui,page}.js, ruta rota, no
  // relacionado con clientes ni con el transporte HTTP de F32) que se
  // dispara en cualquier carga de /workspace/, independientemente del tab
  // al que se navegue despues. Fuera de alcance de este spec -- flageado
  // por separado. Acotar el listener aqui evita un falso positivo.
  const checkErrors = await expectNoConsoleErrors(page, 'clientes');

  // Panel HTMX real: #clientes-panel (hx-trigger="load, cliente-updated
  // from:body") -- esperar a que la tabla real cargue dentro, no un
  // generico <table> (el shell tiene otros <table> ocultos en tabs
  // hermanos: Contactos/Cartera).
  const tableLocator = page.locator('#clientes-panel table').first();
  await expect(tableLocator).toBeVisible({ timeout: 10000 });

  // Generar timestamp único para el cliente
  const ts = Date.now();
  const clientName = `E2E Test ${ts}`;
  const nit = `9001${ts.toString().slice(-6)}`;

  // **CREAR cliente** -- boton real: data-create-button, hx-get abre el
  // offcanvas (apps/tenant/clientes/templates/tenant/clientes/clientes_list.html:36-42)
  const newBtn = page.locator('[data-create-button][data-module="clientes"]').first();
  await newBtn.click();

  // Offcanvas real: offcanvas_crear_cliente.html -- estos IDs SI coinciden
  // con el markup fuente, verificado.
  await page.waitForSelector('#offcanvas-cliente.show', { timeout: 5000 });
  await page.selectOption('#cliente-tipo_persona', 'JURIDICA');
  await page.selectOption('#cliente-tipo_documento', 'NIT');
  await page.fill('#cliente-numero_documento', nit);
  await page.fill('#cliente-razon_social', clientName);
  await page.selectOption('#cliente-regimen_tributario', 'ORDINARIO');

  // Guardar (clientes.editor.js -> w.clientesAPI.create(), luego dispara
  // el evento que recarga #clientes-panel)
  await page.click('#btn-guardar-cliente');

  // Esperar a que aparezca en la tabla (el panel se recarga via evento
  // cliente-updated -- puede tardar más que un simple re-render local)
  await expect(page.locator(`#clientes-panel:has-text("${clientName}")`)).toBeVisible({ timeout: 10000 });

  // **EDITAR cliente** -- boton real: data-action="edit" data-uuid="..."
  // (apps/tenant/clientes/tables.py:130)
  const editBtn = page.locator(`#clientes-panel tr:has-text("${clientName}") [data-action="edit"]`).first();
  await editBtn.click();

  const editedName = `${clientName} EDITED`;
  await page.waitForSelector('#offcanvas-cliente.show, #offcanvas-editar-cliente.show', { timeout: 5000 });
  const nameInputEdit = page.locator('#cliente-razon_social').first();
  await nameInputEdit.fill(editedName);
  // Regla de negocio real (apps/tenant/clientes/static/clientes/js/clientes.list.js:217-220):
  // deleteCliente() rechaza eliminar un cliente activo -- hay que desactivarlo
  // primero. El checkbox #cliente-activo viene marcado por defecto en el
  // offcanvas de creacion.
  await page.uncheck('#cliente-activo');
  await page.locator('#btn-guardar-cliente, #btn-actualizar-cliente').first().click();

  await expect(page.locator(`#clientes-panel:has-text("${editedName}")`)).toBeVisible({ timeout: 10000 });

  // **ELIMINAR cliente** -- boton real: data-action="delete" data-uuid="..."
  page.once('dialog', (dialog) => dialog.accept());
  const deleteBtn = page.locator(`#clientes-panel tr:has-text("${editedName}") [data-action="delete"]`).first();
  await deleteBtn.click();

  await expect(page.locator(`#clientes-panel:has-text("${editedName}")`)).toBeHidden({ timeout: 10000 });

  // Verificar que no hay errores en consola
  checkErrors();
});
