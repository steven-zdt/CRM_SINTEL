const { test, expect } = require('@playwright/test');
const { login } = require('./_helpers');

// F33.4: consolidacion de los 2 helpers "safe offcanvas" (F33.0 §12b) --
// Sintel.Core.mostrarOffcanvasSeguro se extendio con {action:'show'|'hide'}
// y UIManager.handleOffcanvas ahora delega en el como alias delgado.
// Verifica ambos puntos de entrada contra el mismo elemento offcanvas real
// (creado en la pagina, no dependiente de ningun HTMX partial especifico
// de una app) para confirmar que producen el mismo resultado.

const username = process.env.E2E_USER || 'test_user';
const password = process.env.E2E_PASS || 'test_pass';

test('F33.4: mostrarOffcanvasSeguro show/hide y el alias UIManager.handleOffcanvas funcionan igual', async ({ page }) => {
  await login(page, { username, password });
  await page.goto('/workspace/#dashboard');
  await page.waitForSelector('#tab-dashboard', { state: 'visible', timeout: 10000 });

  const result = await page.evaluate(async () => {
    // Crea un offcanvas real de prueba en el DOM.
    const el = document.createElement('div');
    el.className = 'offcanvas offcanvas-end';
    el.id = 'f334-test-offcanvas';
    el.innerHTML = '<div class="offcanvas-body">test</div>';
    document.body.appendChild(el);

    const waitVisible = () => new Promise((r) => setTimeout(r, 350));

    // 1. Sintel.Core.mostrarOffcanvasSeguro -- show (contrato original)
    const inst1 = window.Sintel.Core.mostrarOffcanvasSeguro('f334-test-offcanvas');
    await waitVisible();
    const shownViaHelper = el.classList.contains('show');
    const backdropAfterShow1 = document.querySelectorAll('.offcanvas-backdrop').length;

    // 2. Sintel.Core.mostrarOffcanvasSeguro -- hide (nuevo, F33.4)
    window.Sintel.Core.mostrarOffcanvasSeguro('f334-test-offcanvas', { action: 'hide' });
    await waitVisible();
    const hiddenViaHelper = !el.classList.contains('show');

    // 3. UIManager.handleOffcanvas -- alias, show
    const okShow = window.UIManager.handleOffcanvas('#f334-test-offcanvas', 'show');
    await waitVisible();
    const shownViaAlias = el.classList.contains('show');

    // 4. UIManager.handleOffcanvas -- alias, hide
    const okHide = window.UIManager.handleOffcanvas('#f334-test-offcanvas', 'hide');
    await waitVisible();
    const hiddenViaAlias = !el.classList.contains('show');
    const backdropAfterHide = document.querySelectorAll('.offcanvas-backdrop').length;

    el.remove();

    return {
      instHasShow: typeof inst1?.show === 'function',
      shownViaHelper,
      backdropAfterShow1,
      hiddenViaHelper,
      okShow,
      shownViaAlias,
      okHide,
      hiddenViaAlias,
      backdropAfterHide,
    };
  });

  expect(result.instHasShow).toBe(true);
  expect(result.shownViaHelper).toBe(true);
  expect(result.backdropAfterShow1).toBe(1);
  expect(result.hiddenViaHelper).toBe(true);
  expect(result.okShow).toBe(true);
  expect(result.shownViaAlias).toBe(true);
  expect(result.okHide).toBe(true);
  expect(result.hiddenViaAlias).toBe(true);
  expect(result.backdropAfterHide).toBe(0);
});
