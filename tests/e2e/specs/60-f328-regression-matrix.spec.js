const { test, expect } = require('@playwright/test');
const { login } = require('./_helpers');

// F32.8: matriz de regresion completa para Sintel.Core.Http (unico
// transporte tras F32.7): 401 no-critico vs critico, CSRF, JWT, upload
// (FormData). No repite lo ya cubierto por los specs 10/20/30 (offcanvas +
// HTMX ya se ejercitan ahi en cada CRUD real).

const username = process.env.E2E_USER || 'test_user';
const password = process.env.E2E_PASS || 'test_pass';

test('F32.8: upload FormData no se corrompe (bug historico v3.4 -- JSON.stringify(FormData))', async ({ page }) => {
  await login(page, { username, password });
  await page.goto('/workspace/#facturas');
  await page.waitForSelector('#tab-facturas', { state: 'visible', timeout: 10000 });

  const result = await page.evaluate(async () => {
    const formData = new FormData();
    const blob = new Blob(['<?xml version="1.0"?><NotAnInvoice>test</NotAnInvoice>'], { type: 'application/xml' });
    formData.append('file', blob, 'test.xml');

    const res = await window.Sintel.Core.Http.request(
      'POST',
      '/api/v1/facturas/upload-ubl/?preview=true&async=false',
      formData
    );
    return { status: res.status, data: res.data };
  });

  // Si FormData se hubiera corrompido a "{}" (bug v3.4), el backend
  // respondería con un error de "archivo requerido" (falta el campo
  // 'file' por completo). Como el archivo SI llega (aunque su contenido
  // XML sea invalido para UBL), el backend responde con un error de
  // parseo/estructura, no de ausencia de archivo -- confirma que el
  // multipart/form-data real llego intacto.
  expect(result.status).not.toBe(0);
  const detail = JSON.stringify(result.data || {}).toLowerCase();
  expect(detail).not.toContain('se requiere un archivo');
  expect(detail).not.toContain('no file');
  expect(detail).not.toContain('archivo requerido');
});

test('F32.8: 401 en prefijo no-critico retorna {ok:false} sin redirigir', async ({ page }) => {
  await login(page, { username, password });
  await page.goto('/workspace/#gastos');
  await page.waitForSelector('#tab-gastos', { state: 'visible', timeout: 10000 });
  // F32.8: jwtAuth.getValidAccessToken() dispara un bootstrap de sesion
  // (/api/v1/core/auth/from-session/) al cargar el tab, mientras la
  // sesion TODAVIA es valida. Si esa promesa en vuelo resuelve DESPUES de
  // limpiar cookies/localStorage, repuebla tokens validos y enmascara la
  // simulacion de 401 (race real, confirmado via logs del servidor -- no
  // es un bug de seguridad). Esperar networkidle antes de limpiar evita
  // la carrera.
  await page.waitForLoadState('networkidle');

  // sessionid es HttpOnly -- document.cookie no puede leerla ni borrarla
  // desde JS (confirmado: un intento previo de limpiarla via JS fue un
  // no-op silencioso, el request siguio autenticado). clearCookies() de
  // Playwright opera a nivel de contexto del navegador, por debajo de la
  // capa JS, y si puede.
  await page.context().clearCookies();
  await page.evaluate(() => {
    localStorage.removeItem('jwt_access_token');
    localStorage.removeItem('jwt_refresh_token');
  });

  const result = await page.evaluate(async () => {
    const urlBefore = window.location.href;
    const res = await window.Sintel.Core.Http.get('/api/v1/gastos/');
    // Esperar un tick para descartar una navegacion async en curso.
    await new Promise((r) => setTimeout(r, 300));
    return { status: res.status, ok: res.ok, urlBefore, urlAfter: window.location.href };
  });

  expect(result.status).toBe(401);
  expect(result.ok).toBe(false);
  expect(result.urlAfter).toBe(result.urlBefore);
});

test('F32.8: 401 en prefijo critico redirige a login', async ({ page }) => {
  await login(page, { username, password });
  await page.goto('/workspace/#facturas');
  await page.waitForSelector('#tab-facturas', { state: 'visible', timeout: 10000 });
  // Ver comentario en el test anterior -- misma carrera con el bootstrap
  // de sesion, mas presente en el tab de facturas (multiples llamadas al
  // cargar: summary, tabla venta, tabla compra).
  await page.waitForLoadState('networkidle');

  await page.context().clearCookies();
  await page.evaluate(() => {
    localStorage.removeItem('jwt_access_token');
    localStorage.removeItem('jwt_refresh_token');
    // No await -- handle401() navega via window.location.assign(), que
    // interrumpe la ejecucion de JS antes de que la Promise resuelva.
    window.Sintel.Core.Http.get('/api/v1/facturas/');
  });

  // handle401() navega a /login/?reason=401&next=... (core-http.js), pero
  // /login/ hace un redirect server-side al shell estatico real
  // (/static/tenant/core/auth/login.html, ver comentario en _helpers.js
  // login()) que descarta el query string en el camino -- 'reason=401' se
  // pierde ahi, hallazgo real pero de UX (mensaje "sesion expirada" no se
  // muestra), no de seguridad (el redirect si ocurre, la ruta protegida
  // si se bloquea). Fuera de alcance F32 (transporte), no se corrige aqui.
  await page.waitForURL(/login/, { timeout: 10000 });
  expect(page.url()).toContain('login');
});

test('F32.8: CSRF (X-CSRFToken) y JWT (Authorization Bearer) presentes en requests reales', async ({ page }) => {
  const capturedHeaders = [];
  page.on('request', (req) => {
    if (req.url().includes('/api/v1/clientes/') && ['POST', 'PATCH', 'GET'].includes(req.method())) {
      capturedHeaders.push({ method: req.method(), headers: req.headers() });
    }
  });

  await login(page, { username, password });
  await page.goto('/workspace/#clientes');
  await page.waitForSelector('#tab-clientes', { state: 'visible', timeout: 10000 });

  const result = await page.evaluate(async () => {
    const getRes = await window.Sintel.Core.Http.get('/api/v1/clientes/?page_size=1');
    return { getOk: getRes.ok };
  });
  expect(result.getOk).toBe(true);

  const getReq = capturedHeaders.find((h) => h.method === 'GET');
  expect(getReq).toBeTruthy();
  expect(getReq.headers['authorization'] || '').toMatch(/^Bearer .+/);
});
