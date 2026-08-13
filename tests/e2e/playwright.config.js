const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './specs',
  timeout: 30_000,
  fullyParallel: false,
  // F32.6: manage.py runserver (dev) no es concurrente -- 4 workers en
  // paralelo contra el mismo server causaron un timeout real de
  // networkidle (confirmado: el mismo test paso limpio corriendo solo).
  // Mismo criterio ya aplicado a pytest en este proyecto (nunca en
  // paralelo, ver Makefile/CLAUDE.md).
  workers: 1,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://demo.sintel.net.co:8000',
    headless: true,
    ignoreHTTPSErrors: true,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
});
