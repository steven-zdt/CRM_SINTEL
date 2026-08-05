# E2E Tests — CRM Sintel con Playwright

Suite de smoke tests E2E que validan:
- ✅ `window.http` v3.4 cargado y disponible
- ✅ CRUD de Clientes (crear, editar, eliminar)
- ✅ CRUD de Productos en Inventario
- ✅ CRUD de Cuentas en Contabilidad
- ✅ Editar Tenant desde consola pública

## Setup

```bash
cd tests/e2e

# Instalar dependencias
npm install

# Descargar navegadores (Chromium)
npx playwright install chromium
```

## Ejecución

### Modo headless (por defecto)
```bash
# Variable de entorno opcional
E2E_BASE_URL=http://demo.sintel.net.co:8000 \
E2E_USER=test_user \
E2E_PASS=test_pass \
E2E_PUBLIC_URL=http://sintel.net.co:8000 \
E2E_ADMIN_USER=admin \
E2E_ADMIN_PASS=admin \
npm test
```

### Modo headed (ve el navegador)
```bash
npm run test:headed
```

### Modo UI (debugging interactivo)
```bash
npm run test:ui
```

### Modo debug (paso a paso)
```bash
npm run test:debug
```

## Estructura

```
tests/e2e/
├── package.json                          # Dependencias
├── playwright.config.js                  # Configuración
├── specs/
│   ├── _helpers.js                       # Funciones reutilizables
│   ├── 00-http-loaded.spec.js           # ✅ Verifica window.http v3.4
│   ├── 10-clientes-crud.spec.js         # ✅ CRUD de clientes
│   ├── 20-inventario-productos-crud.spec.js  # ✅ CRUD de productos
│   ├── 30-contabilidad-cuenta-crud.spec.js   # ✅ CRUD de cuentas
│   └── 40-tenant-edit.spec.js           # ✅ Editar tenant (consola pública)
├── test-results/                         # Reportes (generado)
└── README.md                             # Este archivo
```

## Variables de entorno

| Variable | Descripción | Defecto |
|----------|---|---|
| `E2E_BASE_URL` | URL base del tenant demo | `http://demo.sintel.net.co:8000` |
| `E2E_USER` | Usuario de prueba del tenant | `test_user` |
| `E2E_PASS` | Contraseña del usuario | `test_pass` |
| `E2E_PUBLIC_URL` | URL base de la consola pública | `http://sintel.net.co:8000` |
| `E2E_ADMIN_USER` | Usuario admin de consola pública | `admin` |
| `E2E_ADMIN_PASS` | Contraseña del admin | `admin` |

## Fixture de datos

Antes de ejecutar, asegurar que existen:
- Tenant `demo` con usuario `test_user:test_pass`
- Admin en consola pública `admin:admin`

```bash
# Crear datos de prueba (si es necesario)
python manage.py createsuperuser  # Para admin consola pública
python manage.py shell

# Dentro del shell:
from django.contrib.auth import get_user_model
from apps.public.tenants.models import Client
User = get_user_model()

# Crear usuario de prueba del tenant demo
User.objects.create_user(username='test_user', password='test_pass', email='test@demo.com')
```

## Output

Los tests generan:
- `test-results/` — Reportes de ejecución
- Traces en caso de fallos (para debugging)
- Screenshots solo si falla algún test

## CI/CD Integration

Ejemplo para GitHub Actions (`.github/workflows/e2e.yml`):

```yaml
name: E2E Tests
on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: cd tests/e2e && npm install

      - name: Install Playwright browsers
        run: cd tests/e2e && npx playwright install --with-deps chromium

      - name: Run E2E tests
        run: cd tests/e2e && npm test
        env:
          E2E_BASE_URL: 'http://demo.sintel.net.co:8000'
          E2E_USER: 'test_user'
          E2E_PASS: 'test_pass'
          E2E_PUBLIC_URL: 'http://sintel.net.co:8000'
          E2E_ADMIN_USER: 'admin'
          E2E_ADMIN_PASS: 'admin'

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: tests/e2e/test-results/
```

## Troubleshooting

### "Browser not installed"
```bash
npx playwright install chromium
```

### "Connection refused: localhost:8000"
Verificar que el servidor Django está corriendo:
```bash
python manage.py runserver 0.0.0.0:8000
```

### "test_user no existe"
Crear el usuario en el tenant demo:
```bash
python manage.py shell < setup_test_user.py
```

### Selectores no funcionan
Los tests usan selectores tolerantes (`.first()`, alternativas). Si alguno falla:
1. Inspeccionar el HTML en DevTools
2. Actualizar el selector en el spec
3. Preferentemente, agregar `data-test="..."` al HTML para estabilidad

---

**Última actualización:** Sprint 1 — Fase 6  
**Documentación:** [SPRINT_1_DESBLOQUEAR_CRUD.md](../../documentacion/SPRINT_1_DESBLOQUEAR_CRUD.md)
