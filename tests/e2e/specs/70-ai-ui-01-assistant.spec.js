const { test, expect } = require('@playwright/test');
const { login, expectNoConsoleErrors } = require('./_helpers');

// SINTEL-AI-UI-01: primera superficie de UI del AI Engine existente (AI-06).
// Este spec NO depende de que AI_ENABLED/ANTHROPIC_API_KEY esten configurados
// en el entorno -- en ese caso POST /api/v1/ai/ask/ responde 403
// PERMISSION_DENIED (ver apps/services/ai/orchestrator/form_assistant.py),
// y este spec verifica que el panel lo muestre como un mensaje de error
// amigable (Fase 3/8 de la mision) en vez de romperse. La respuesta 200
// con datos reales de una tool (Fase 10, flujo con AI_ENABLED=true + API
// key real) requiere un entorno con esas credenciales -- fuera del alcance
// de lo que este spec puede probar de forma determinista/reproducible.

const username = process.env.E2E_USER || 'test_user';
const password = process.env.E2E_PASS || 'test_pass';

test.describe('SINTEL-AI-UI-01: panel global del Asistente IA', () => {
  test('boton visible, abre el offcanvas y muestra el estado inicial', async ({ page }) => {
    const checkErrors = await expectNoConsoleErrors(page, 'ai-ui-01-open');
    await login(page, { username, password });
    await page.goto('/workspace/#dashboard');
    await page.waitForSelector('#tab-dashboard', { state: 'visible', timeout: 10000 });

    const boton = page.locator('#btn-asistente-ia-toggle');
    await expect(boton).toBeVisible();

    await boton.click();
    const offcanvas = page.locator('#offcanvas-asistente-ia');
    await expect(offcanvas).toHaveClass(/show/, { timeout: 5000 });
    await expect(page.locator('#asistente-ia-empty')).toBeVisible();
    await expect(page.locator('#asistente-ia-empty')).toContainText('Hola. Puedo ayudarte');

    // Aviso de solo lectura (Fase 3) siempre visible en el panel.
    await expect(page.locator('#asistente-ia-contexto')).toContainText('Solo consulta');

    checkErrors();
  });

  test('enviar una pregunta agrega la burbuja del usuario y maneja la respuesta sin romperse', async ({ page }) => {
    await login(page, { username, password });
    await page.goto('/workspace/#dashboard');
    await page.waitForSelector('#tab-dashboard', { state: 'visible', timeout: 10000 });
    await page.click('#btn-asistente-ia-toggle');
    await expect(page.locator('#offcanvas-asistente-ia')).toHaveClass(/show/);

    await page.fill('#asistente-ia-input', 'Que productos tienen menor stock?');
    await page.click('#asistente-ia-enviar');

    // Burbuja del usuario aparece de inmediato, estado vacio desaparece.
    await expect(page.locator('.asistente-ia-msg-usuario').last()).toHaveText('Que productos tienen menor stock?');
    await expect(page.locator('#asistente-ia-empty')).toBeHidden();

    // Cualquiera sea la respuesta real del backend (200 con datos si el
    // entorno tiene AI_ENABLED+API key, o el 403 amigable si no), el panel
    // debe terminar con exactamente una burbuja de respuesta y el input
    // reactivado -- nunca colgado en estado "cargando".
    await expect(page.locator('#asistente-ia-mensajes > .asistente-ia-msg').nth(1)).toBeVisible({ timeout: 15000 });
    await expect(page.locator('#asistente-ia-input')).toBeEnabled();
    await expect(page.locator('#asistente-ia-enviar')).toBeEnabled();
  });

  test('el doble clic no duplica el envio (guard de doble submit)', async ({ page }) => {
    await login(page, { username, password });
    await page.goto('/workspace/#dashboard');
    await page.waitForSelector('#tab-dashboard', { state: 'visible', timeout: 10000 });
    await page.click('#btn-asistente-ia-toggle');
    await expect(page.locator('#offcanvas-asistente-ia')).toHaveClass(/show/);

    await page.fill('#asistente-ia-input', 'busca clientes');
    await page.click('#asistente-ia-enviar');
    // Segundo clic inmediato -- el boton ya deberia estar disabled por _setCargando.
    await page.click('#asistente-ia-enviar', { force: true }).catch(() => {});

    await page.waitForTimeout(1500);
    await expect(page.locator('.asistente-ia-msg-usuario')).toHaveCount(1);
  });

  test('un mensaje con markup no se ejecuta como HTML (XSS)', async ({ page }) => {
    await login(page, { username, password });
    await page.goto('/workspace/#dashboard');
    await page.waitForSelector('#tab-dashboard', { state: 'visible', timeout: 10000 });
    await page.click('#btn-asistente-ia-toggle');
    await expect(page.locator('#offcanvas-asistente-ia')).toHaveClass(/show/);

    const payload = '<img src=x onerror="window.__ai_ui_01_xss=true">';
    await page.fill('#asistente-ia-input', payload);
    await page.click('#asistente-ia-enviar');

    await expect(page.locator('.asistente-ia-msg-usuario').last()).toHaveText(payload);
    const huboXss = await page.evaluate(() => window.__ai_ui_01_xss === true);
    expect(huboXss).toBe(false);
    // El markup quedo como texto plano, nunca como <img> real dentro de la burbuja.
    const imgCount = await page.locator('.asistente-ia-msg-usuario img').count();
    expect(imgCount).toBe(0);
  });

  test('el boton de cerrar oculta el offcanvas', async ({ page }) => {
    await login(page, { username, password });
    await page.goto('/workspace/#dashboard');
    await page.waitForSelector('#tab-dashboard', { state: 'visible', timeout: 10000 });
    await page.click('#btn-asistente-ia-toggle');
    const offcanvas = page.locator('#offcanvas-asistente-ia');
    await expect(offcanvas).toHaveClass(/show/);

    await page.click('#offcanvas-asistente-ia .btn-close');
    await expect(offcanvas).not.toHaveClass(/show/, { timeout: 5000 });
  });
});
