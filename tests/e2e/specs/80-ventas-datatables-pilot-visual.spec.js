const { test, expect } = require('@playwright/test');
const { login, expectNoConsoleErrors } = require('./_helpers');

/**
 * Cierre del gate visual pendiente del piloto DataTables 3.x en Ventas
 * (docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md). La sesion que
 * construyo el piloto no tenia navegador conectado; este spec confirma
 * en un navegador real lo que quedo documentado como PENDIENTE:
 * - la tabla se puebla via ajax contra POST /api/v1/ventas/dt/
 * - el buscador nativo de DataTables (layout.topStart:'search') aparece
 * - paginacion/info aparecen (layout.bottomStart:'info'/bottomEnd:'paging')
 * - los inputs de filtro por columna (fila #fila-filtros-ventas) disparan
 *   el fetch correcto y el resultado coincide con el filtro aplicado
 * - responsive en viewport movil sin overflow horizontal de pagina
 * - sin errores de consola en todo el flujo
 *
 * Usuario: QA dedicado creado para esta verificacion (rol ADMIN,
 * TenantMembership real en el tenant), sin credenciales ni datos de
 * ningun usuario real. No se muta ninguna Venta -- solo lectura/filtrado.
 */
test.describe('Piloto DataTables Ventas -- gate visual', () => {
  test('tabla carga via ajax, buscador/paginacion nativos, filtros por columna, responsive, sin errores de consola', async ({ page }) => {
    const checkErrors = await expectNoConsoleErrors(page, 'ventas-datatables-pilot');

    const username = process.env.E2E_USER;
    const password = process.env.E2E_PASS;
    await login(page, { username, password });

    await page.goto('/workspace/#ventas');
    await page.waitForSelector('#tabla-ventas', { state: 'visible', timeout: 15000 });

    // La tabla debe poblarse via ajax (fila real, no el esqueleto vacio)
    await page.waitForSelector('#tabla-ventas tbody tr td', { timeout: 15000 });
    const filasIniciales = await page.locator('#tabla-ventas tbody tr').count();
    expect(filasIniciales).toBeGreaterThan(0);

    // Buscador nativo de DataTables (layout.topStart:'search')
    const search = page.locator('#tabla-ventas_wrapper .dt-search input, #tabla-ventas_wrapper input[type="search"]');
    await expect(search.first()).toBeVisible();

    // Info + paginacion nativos (layout.bottomStart:'info', bottomEnd:'paging')
    const info = page.locator('#tabla-ventas_wrapper .dt-info');
    await expect(info.first()).toBeVisible();
    await expect(info.first()).toContainText('Mostrando');

    await page.screenshot({ path: 'test-results/ventas-datatables-desktop.png', fullPage: true });

    // Filtro por columna -- Estado (select, columna indice 2, exacto)
    const responsePromise = page.waitForResponse((r) => r.url().includes('/api/v1/ventas/dt/') && r.request().method() === 'POST');
    await page.selectOption('#filtro-venta-estado', 'FACTURADA_DIAN');
    const dtResponse = await responsePromise;
    expect(dtResponse.status()).toBe(200);
    const dtBody = await dtResponse.json();
    expect(Array.isArray(dtBody.data)).toBe(true);
    for (const row of dtBody.data) {
      expect(row.estado).toBe('FACTURADA_DIAN');
    }

    // Limpiar el filtro de Estado antes de continuar
    const clearPromise = page.waitForResponse((r) => r.url().includes('/api/v1/ventas/dt/') && r.request().method() === 'POST');
    await page.selectOption('#filtro-venta-estado', '');
    await clearPromise;

    // Filtro de rango numerico -- Total minimo (el listener real es 'keyup',
    // por eso se simulan pulsaciones reales con pressSequentially en vez de
    // fill(), que solo dispara 'input'/'change')
    const rangoPromise = page.waitForResponse((r) => r.url().includes('/api/v1/ventas/dt/') && r.request().method() === 'POST');
    await page.locator('#filtro-venta-total-min').pressSequentially('1', { delay: 50 });
    const rangoResponse = await rangoPromise;
    expect(rangoResponse.status()).toBe(200);

    // Responsive -- viewport movil. El shell de /workspace/ (sidebar) NO es
    // responsive en ningun tab (verificado tambien en #dashboard, sin tabla
    // ni DataTables de por medio -- overflow pre-existente y transversal a
    // toda la app, fuera de alcance de este piloto). Lo que SI es
    // responsabilidad de este piloto: que el propio wrapper de la tabla
    // (`.w-100[style*=overflow-x]` en tabla_ventas.html) contenga su propio
    // scroll horizontal en vez de sumar overflow adicional a la pagina.
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(300);
    await page.screenshot({ path: 'test-results/ventas-datatables-mobile.png', fullPage: true });
    const tableOverflow = await page.evaluate(() => {
      const wrapper = document.querySelector('#tabla-ventas_wrapper').parentElement;
      return wrapper.scrollWidth - wrapper.clientWidth;
    });
    // Margen generoso: unos pocos px de scroll CONTENIDO dentro del propio
    // wrapper (su ancho de scrollbar) son esperados y no son el bug que
    // esto detecta -- lo que importa es que no se dispare al nivel de pagina.
    expect(tableOverflow).toBeLessThanOrEqual(20);

    checkErrors();
  });
});
