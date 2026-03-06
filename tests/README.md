# Suite de Pruebas del Proyecto SINTEL

Este directorio contiene la suite completa de pruebas del proyecto, siguiendo estrictamente `documentacion/arquitectura_general.md`.

## Estructura

```
tests/
├── docker/                    # Tests de Docker (lint, build, estructura, health)
│   ├── __init__.py
│   ├── test_docker.py
│   └── container-structure-test.yaml
└── README.md                  # Este archivo

apps/
├── config/
│   └── tests/                 # Clases base de testing
│       ├── __init__.py
│       ├── base_public.py     # PublicAPITestCase - Para apps públicas (SHARED_APPS)
│       └── base_tenant.py     # TenantAPITestCase - Para apps tenant (TENANT_APPS)
│
├── public/
│   ├── tenants/
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_api_tenants.py
│   │       └── test_templates.py
│   ├── accounts/
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_api_accounts.py
│   │       └── test_templates.py
│   └── impuestos/
│       └── tests/
│           ├── __init__.py
│           ├── test_api_impuestos.py
│           └── test_templates.py
│
└── tenant/
    ├── empresa/
    │   └── tests/
    │       ├── __init__.py
    │       ├── test_api_empresa.py
    │       └── test_templates.py
    ├── facturas/
    │   └── tests/
    │       ├── __init__.py
    │       ├── test_api_facturas.py
    │       └── test_templates.py
    └── contabilidad/
        └── tests/
            ├── __init__.py
            ├── test_api_contabilidad.py
            └── test_templates.py
```

## Clases Base

### `apps.config.tests.base_public.PublicAPITestCase`

Clase base para tests de apps públicas (SHARED_APPS):
- Hereda de `APITestCase` (DRF)
- Proporciona `APIClient` configurado
- Helpers: `json()`, `assertJSONResponse()`, `assertPaginationFormat()`
- Usuario admin por defecto

**Uso:**
```python
from apps.config.tests.base_public import PublicAPITestCase

class MyPublicTests(PublicAPITestCase):
    def test_something(self):
        response = self.json('get', '/api/public/v1/endpoint/')
        self.assertJSONResponse(response)
```

### `apps.config.tests.base_tenant.TenantAPITestCase`

Clase base para tests de apps tenant (TENANT_APPS):
- Hereda de `TenantTestCase` (django-tenants)
- Proporciona `TenantClient` con dominio configurado automáticamente
- Helpers: `tget()`, `tpost()`, `tput()`, `tpatch()`, `tdelete()`
- Aislamiento automático por esquema
- Helper `assertTenantIsolation()` para verificar aislamiento
- Método `setup_tenant()` para configurar campos adicionales del tenant

**Uso:**
```python
from apps.config.tests.base_tenant import TenantAPITestCase

class MyTenantTests(TenantAPITestCase):
    def test_something(self):
        response = self.tget('/api/v1/endpoint/')
        self.assertJSONResponse(response)
```

## Ejecutar Tests

### Todos los tests

```bash
docker compose exec web python manage.py test
```

**Nota:** El proyecto usa `DiscoverRunner` estándar de Django (por defecto). django-tenants no requiere un test runner especial; usa `TenantTestCase` y `TenantClient` para manejar tenants en tests.

### Tests de una app específica

```bash
docker compose exec web python manage.py test apps.public.tenants.tests
docker compose exec web python manage.py test apps.tenant.empresa.tests
```

### Tests con verbosidad

```bash
docker compose exec web python manage.py test -v 2
```

### Tests de Docker

```bash
# Lint del Dockerfile
make docker-lint

# Tests de Docker (build, smoke run, etc.)
make docker-test

# Container Structure Tests
make docker-cst
```

### Con pytest (si está instalado)

```bash
docker compose exec web pytest apps/public/tenants/tests/ -v
docker compose exec web pytest apps/tenant/empresa/tests/ -v
```

## Cobertura de Tests

### Apps Públicas (SHARED_APPS)

1. **apps.public.tenants**
   - ✅ ReadOnly para Client y Domain (list/detail)
   - ✅ 405 en POST/PUT/DELETE
   - ✅ Paginación y filtros
   - ✅ Smoke tests de templates

2. **apps.public.accounts**
   - ✅ CRUD completo de User
   - ✅ Endpoint `me/` (perfil del usuario autenticado)
   - ✅ Email único y username autogenerado
   - ✅ Paginación y filtros
   - ✅ Smoke tests de templates

3. **apps.public.impuestos**
   - ✅ ReadOnly para todos los modelos (TipoImpuesto, TarifaIVA, etc.)
   - ✅ 405 en POST/PUT/DELETE
   - ✅ Paginación y filtros
   - ✅ Smoke tests de templates

### Apps Tenant (TENANT_APPS)

1. **apps.tenant.empresa**
   - ✅ CRUD completo
   - ✅ Acción `activas/` (GET /api/v1/empresas/activas/)
   - ✅ Paginación y filtros
   - ✅ Aislamiento por tenant
   - ✅ Smoke tests de templates

2. **apps.tenant.facturas**
   - ✅ CRUD completo de Factura e ItemFactura
   - ✅ Acción `por_estado/` (GET /api/v1/facturas/por_estado/?estado=...)
   - ✅ Acción `cambiar_estado/` (POST /api/v1/facturas/{id}/cambiar_estado/)
   - ✅ Paginación y filtros
   - ✅ Smoke tests de templates

3. **apps.tenant.contabilidad**
   - ✅ CRUD completo de CuentaContable, AsientoContable, MovimientoContable
   - ✅ Acción `aprobar/` (POST /api/v1/asientos-contables/{id}/aprobar/)
   - ✅ Validación de balance (debe = haber)
   - ✅ Paginación y filtros
   - ✅ Smoke tests de templates

### Tests de Docker

1. **Docker Lint**
   - ✅ Lint del Dockerfile con Hadolint
   - ✅ Target `make docker-lint`

2. **Build & Smoke Run**
   - ✅ `docker compose build` funciona
   - ✅ `check_migrations` funciona en el contenedor (Server Guard)

3. **Container Structure Tests**
   - ✅ Metadata (puertos, entrypoint, workdir)
   - ✅ File existence (manage.py, config/settings.py, apps/config/api/, etc.)
   - ✅ Command tests (Python version, Django check, check_migrations)

4. **Healthchecks**
   - ✅ Healthcheck de DB configurado en docker-compose.yaml

## Principios Arquitectónicos Verificados

✅ **API-First**: Todos los endpoints devuelven JSON, no templates HTML  
✅ **Multi-Tenant**: Aislamiento verificado entre tenants  
✅ **Service Layer**: Lógica de negocio en `apps/services/`  
✅ **Cero Signals**: No se usan Django signals  
✅ **Settings Simple**: Configuración declarativa en `settings.py`  
✅ **Server Guard**: `check_migrations` bloquea arranque con migraciones pendientes  

## Referencias

- [Django REST Framework Testing](https://www.django-rest-framework.org/api-guide/testing/)
- [django-tenants Testing](https://django-tenants.readthedocs.io/en/latest/testing.html)
- [Container Structure Tests](https://github.com/GoogleContainerTools/container-structure-test)
- [Hadolint](https://github.com/hadolint/hadolint)
