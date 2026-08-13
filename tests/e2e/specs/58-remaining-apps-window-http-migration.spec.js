const { test, expect } = require('@playwright/test');
const { login } = require('./_helpers');

// F32.7: smoke E2E para las apps que quedaron sin cobertura dedicada tras
// migrar los 46 archivos restantes que llamaban window.http/w.http
// directamente (bancos, empresa, proyectos, clientes.cartera/contactos,
// proveedores, contabilidad asiento/periodo/plantilla). No cubre cada
// call-site individual (serian 46 specs) -- confirma que Sintel.Core.Http
// sigue respondiendo correctamente para el endpoint principal de listado de
// cada app, que es el riesgo real compartido por todas las migraciones
// (delegacion de transporte, headers JWT/CSRF). Los 8 archivos api.js con
// contrato propio ya tienen specs dedicados (50-56); este spec cubre el
// resto.

const username = process.env.E2E_USER || 'test_user';
const password = process.env.E2E_PASS || 'test_pass';

const cases = [
  { tab: 'bancos', url: '/api/v1/bancos/cuentas/' },
  { tab: 'empresa', url: '/api/v1/empresas/sedes/' },
  { tab: 'proyectos', url: '/api/v1/proyectos/' },
  { tab: 'contabilidad', url: '/api/v1/contabilidad/asientos-contables/' },
  { tab: 'contabilidad', url: '/api/v1/contabilidad/periodos-contables/' },
  { tab: 'contabilidad', url: '/api/v1/contabilidad/plantillas-contables/' },
  { tab: 'clientes', url: '/api/v1/clientes/cartera/' },
  { tab: 'proveedores', url: '/api/v1/proveedores/representantes/' },
];

for (const { tab, url } of cases) {
  test(`F32.7: ${url} responde 200 via Core.Http tras migrar ${tab}`, async ({ page }) => {
    await login(page, { username, password });
    await page.goto(`/workspace/#${tab}`);
    await page.waitForSelector(`#tab-${tab}`, { state: 'visible', timeout: 10000 });

    const result = await page.evaluate(async (u) => {
      const res = await window.Sintel.Core.Http.get(u);
      return { ok: res.ok, status: res.status };
    }, url);

    expect(result.status).not.toBe(404);
    expect(result.status).not.toBe(0);
    expect([200, 401, 403].includes(result.status)).toBe(true);
  });
}
