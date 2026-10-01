// Verificacion del modal "Vincular Cotización" (seleccion multiple via
// checkboxes) en "Nueva Requisición de Compra", usando la URL exacta que
// pidio el usuario: http://admin.sintel.net.co/workspace/#compras
const { chromium } = require('playwright');

const BASE_URL = process.env.E2E_BASE_URL || 'http://admin.sintel.net.co';
const EMAIL = process.env.E2E_USER;
const PASSWORD = process.env.E2E_PASS;

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  const consoleErrors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
  page.on('pageerror', (err) => consoleErrors.push('pageerror: ' + err.message));

  await page.goto(BASE_URL + '/static/tenant/core/auth/login.html');
  await page.fill('#login_email', EMAIL);
  await page.fill('#login_password', PASSWORD);
  await page.click('#login_submit_btn');
  await page.waitForURL(/\/(dashboard|workspace|console|clientes)\/?/, { timeout: 20000 });

  console.log('== Navegar directo a', BASE_URL + '/workspace/#compras', '==');
  await page.goto(BASE_URL + '/workspace/#compras');
  await page.waitForSelector('#tab-compras', { state: 'visible', timeout: 10000 });
  await page.waitForSelector('#subtab-requisiciones-btn', { state: 'attached', timeout: 20000 });
  await page.click('#subtab-requisiciones-btn');

  const btn = page.locator('[hx-get="/api/v1/compras/requisiciones/render-offcanvas/crear/"]');
  await btn.click();
  await page.waitForSelector('#offcanvas-requisicion-crear.show', { timeout: 10000 });
  await page.waitForFunction(() => document.querySelectorAll('#req-plantilla option').length > 1, { timeout: 10000 });

  console.log('== Abrir el modal "Vincular Cotización" ==');
  const modalExisteAntes = await page.evaluate(() => !!document.getElementById('modal-vincular-cotizacion'));
  console.log('Modal existe en el DOM:', modalExisteAntes);

  await page.click('#btn-mostrar-modal-cotizacion');
  await page.waitForSelector('#modal-vincular-cotizacion.show', { timeout: 5000 });
  console.log('Modal visible (.show):', true);

  await page.waitForFunction(() => {
    const el = document.querySelector('#req-cotizacion-buscar-resultados');
    return el && el.querySelectorAll('.req-cotizacion-checkbox').length > 0;
  }, { timeout: 10000 });

  const totalCheckboxes = await page.locator('.req-cotizacion-checkbox').count();
  console.log('Checkboxes de resultados renderizados:', totalCheckboxes);

  console.log('== Marcar 2 cotizaciones (multi-select) ==');
  const contadorInicial = await page.locator('#req-cotizacion-modal-contador').textContent();
  console.log('Contador inicial:', contadorInicial);
  const btnAgregarDisabledInicial = await page.evaluate(() => document.getElementById('btn-agregar-cotizaciones-seleccionadas').disabled);
  console.log('Boton "Agregar Seleccionadas" disabled al inicio:', btnAgregarDisabledInicial);

  const checkboxes = page.locator('.req-cotizacion-checkbox');
  await checkboxes.nth(0).check();
  await checkboxes.nth(1).check();
  await page.waitForTimeout(200);

  const contadorTras2 = await page.locator('#req-cotizacion-modal-contador').textContent();
  console.log('Contador tras marcar 2:', contadorTras2);
  const btnAgregarDisabledTras2 = await page.evaluate(() => document.getElementById('btn-agregar-cotizaciones-seleccionadas').disabled);
  console.log('Boton "Agregar Seleccionadas" disabled tras marcar 2:', btnAgregarDisabledTras2);

  await page.screenshot({
    path: 'C:/Users/steve/AppData/Local/Temp/claude/D--Proyectos-crm-sintel/f8b63dd6-ea9d-440d-9f6b-a5420dbe9be4/scratchpad/modal_cotizacion_abierto.png',
    fullPage: false,
  });

  console.log('== Probar buscar dentro del modal (no debe perder las marcas) ==');
  const numerosMarcados = await page.evaluate(() => Array.from(document.querySelectorAll('.req-cotizacion-checkbox:checked')).map((c) => c.getAttribute('data-numero')));
  console.log('Numeros marcados antes de buscar:', numerosMarcados);
  await page.fill('#req-cotizacion-buscar-input', 'zzz-no-deberia-existir-nada');
  await page.waitForTimeout(300);
  const contadorTrasBuscarVacio = await page.locator('#req-cotizacion-modal-contador').textContent();
  console.log('Contador tras buscar algo sin resultados (deben seguir las 2 marcadas):', contadorTrasBuscarVacio);
  await page.fill('#req-cotizacion-buscar-input', '');
  await page.waitForTimeout(300);
  const checkboxesTrasLimpiarBusqueda = await page.evaluate(() => Array.from(document.querySelectorAll('.req-cotizacion-checkbox:checked')).map((c) => c.getAttribute('data-numero')));
  console.log('Checkboxes marcados tras limpiar busqueda (deben persistir):', checkboxesTrasLimpiarBusqueda);

  console.log('== Confirmar "Agregar Seleccionadas" (debe cerrar el modal solo) ==');
  await page.click('#btn-agregar-cotizaciones-seleccionadas');
  await page.waitForTimeout(800);
  const modalSigueAbierto = await page.evaluate(() => document.getElementById('modal-vincular-cotizacion')?.classList.contains('show'));
  console.log('Modal sigue abierto tras Agregar Seleccionadas:', modalSigueAbierto);

  const vinculadasEnFormulario = await page.locator('#req-cotizacion-lista').innerText();
  console.log('Cotizaciones vinculadas transportadas al formulario:\n' + vinculadasEnFormulario);

  const filasItems = await page.evaluate(() => Array.from(document.querySelectorAll('#items-req-tbody tr')).map((tr) => ({
    desc: tr.querySelector('.req-item-desc')?.value,
    origen: tr.querySelector('.req-item-origen')?.textContent?.trim(),
  })));
  console.log('Items sincronizados desde las 2 cotizaciones:', JSON.stringify(filasItems, null, 2));

  console.log('== Reabrir el modal: debe arrancar limpio (sin marcas viejas) ==');
  await page.click('#btn-mostrar-modal-cotizacion');
  await page.waitForSelector('#modal-vincular-cotizacion.show', { timeout: 5000 });
  await page.waitForTimeout(500);
  const contadorReapertura = await page.locator('#req-cotizacion-modal-contador').textContent();
  const checkboxesMarcadosReapertura = await page.evaluate(() => document.querySelectorAll('.req-cotizacion-checkbox:checked').length);
  console.log('Contador al reabrir (debe ser "0 seleccionadas"):', contadorReapertura, '| checkboxes marcados:', checkboxesMarcadosReapertura);
  const yaVinculadasNoAparecen = await page.evaluate((numeros) => {
    const textos = Array.from(document.querySelectorAll('.req-cotizacion-checkbox')).map((c) => c.getAttribute('data-numero'));
    return numeros.every((n) => !textos.includes(n));
  }, numerosMarcados);
  console.log('Las 2 ya vinculadas NO vuelven a aparecer en la busqueda:', yaVinculadasNoAparecen);

  console.log('== Cancelar el modal (X) ==');
  await page.click('#modal-vincular-cotizacion .btn-close');
  await page.waitForTimeout(500);
  const modalCerradoTrasX = await page.evaluate(() => !document.getElementById('modal-vincular-cotizacion')?.classList.contains('show'));
  console.log('Modal cerrado tras click en X:', modalCerradoTrasX);

  await page.screenshot({
    path: 'C:/Users/steve/AppData/Local/Temp/claude/D--Proyectos-crm-sintel/f8b63dd6-ea9d-440d-9f6b-a5420dbe9be4/scratchpad/modal_cotizacion_final.png',
    fullPage: false,
  });

  console.log('== Errores de consola acumulados ==');
  console.log(consoleErrors.length ? consoleErrors.join('\n') : '(ninguno)');

  await browser.close();
})().catch((err) => {
  console.error('FALLO:', err);
  process.exit(1);
});
