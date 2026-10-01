const { chromium } = require('playwright');
const BASE_URL = process.env.E2E_BASE_URL;
const EMAIL = process.env.E2E_USER;
const PASSWORD = process.env.E2E_PASS;
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto(BASE_URL + '/static/tenant/core/auth/login.html');
  await page.fill('#login_email', EMAIL);
  await page.fill('#login_password', PASSWORD);
  await page.click('#login_submit_btn');
  await page.waitForURL(/\/(dashboard|workspace|console|clientes)\/?/, { timeout: 20000 });
  await page.goto(BASE_URL + '/workspace/#compras');
  await page.waitForSelector('#tab-compras', { state: 'visible', timeout: 10000 });
  await page.waitForSelector('#subtab-requisiciones-btn', { state: 'attached', timeout: 20000 });
  await page.click('#subtab-requisiciones-btn');
  const btn = page.locator('[hx-get="/api/v1/compras/requisiciones/render-offcanvas/crear/"]');
  await btn.click();
  await page.waitForSelector('#offcanvas-requisicion-crear.show', { timeout: 10000 });
  await page.waitForFunction(() => document.querySelectorAll('#req-plantilla option').length > 1, { timeout: 10000 });
  await page.click('#btn-mostrar-modal-cotizacion');
  await page.waitForFunction(() => document.querySelectorAll('.req-cotizacion-checkbox').length > 0, { timeout: 10000 });

  const idsDup = await page.evaluate(() => {
    return {
      countContador: document.querySelectorAll('#req-cotizacion-modal-contador').length,
      countBtnAgregar: document.querySelectorAll('#btn-agregar-cotizaciones-seleccionadas').length,
      countResultados: document.querySelectorAll('#req-cotizacion-buscar-resultados').length,
      countModal: document.querySelectorAll('#modal-vincular-cotizacion').length,
    };
  });
  console.log('Conteo de IDs (debe ser 1 cada uno):', JSON.stringify(idsDup));

  await page.locator('.req-cotizacion-checkbox').first().check();
  await page.waitForTimeout(300);

  const estadoTrasCheck = await page.evaluate(() => ({
    checkedCount: document.querySelectorAll('.req-cotizacion-checkbox:checked').length,
    contadorTexto: document.getElementById('req-cotizacion-modal-contador')?.textContent,
    btnDisabled: document.getElementById('btn-agregar-cotizaciones-seleccionadas')?.disabled,
  }));
  console.log('Estado tras marcar 1 checkbox:', JSON.stringify(estadoTrasCheck));

  // Disparar change manualmente para descartar problema de evento de Playwright
  await page.evaluate(() => {
    var chk = document.querySelector('.req-cotizacion-checkbox:checked');
    chk.dispatchEvent(new Event('change', { bubbles: true }));
  });
  await page.waitForTimeout(300);
  const estadoTrasDispatchManual = await page.evaluate(() => ({
    contadorTexto: document.getElementById('req-cotizacion-modal-contador')?.textContent,
    btnDisabled: document.getElementById('btn-agregar-cotizaciones-seleccionadas')?.disabled,
  }));
  console.log('Estado tras dispatch manual de change:', JSON.stringify(estadoTrasDispatchManual));

  await browser.close();
})();
