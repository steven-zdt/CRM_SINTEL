# Skill: Testing API — Django Tenants + DRF (SINTEL v1.0)

**Carga cuando:** Escribir, corregir o revisar tests de API en cualquier app de negocio (`apps/tenant/<app>/tests/`).

---

## Base Obligatoria

```python
from django.test import override_settings
from rest_framework import status
from apps.config.tests.base_tenant import TenantAPITestCase

@override_settings(ALLOWED_HOSTS=['*'])
class TestMiModeloAPI(TenantAPITestCase):
    def setUp(self):
        super().setUp()  # SIEMPRE llamar super().setUp() primero
        self.url_list = '/api/v1/<app>/<recurso>/'
        # ... crear fixtures aquí
```

**`@override_settings(ALLOWED_HOSTS=['*'])`** — obligatorio en TODA clase de test. Sin esto, el middleware rechaza el host y devuelve 403/404.

---

## Qué Hace `super().setUp()`

`TenantAPITestCase` (en `apps/config/tests/base_tenant.py`) ya crea automáticamente:

| Qué crea | Dónde | Cómo acceder |
|---|---|---|
| Schema PostgreSQL aislado | `self.tenant.schema_name` | `self.tenant` |
| `User` con rol ADMIN | schema `public` | `self.user` |
| `TenantMembership` ADMIN | schema `public` | — |
| `TenantProfile` ADMIN | schema tenant | — |
| `Empresa` base | schema tenant | `Empresa.objects.first()` |
| `TenantClient` con `HTTP_HOST` | — | `self.client` |
| JWT access token | — | `self.jwt_token` |

**NUNCA usar `self.empresa_id` — no existe en la base.** Obtener la empresa así:

```python
from apps.tenant.empresa.models import Empresa
empresa = Empresa.objects.first()   # dentro del schema tenant activo
```

---

## HTTP Helpers (todos auto-inyectan JWT + HTTP_HOST)

```python
self.tget(url, **kwargs)            # GET
self.tpost(url, data=None, **kwargs) # POST — serializa data como JSON
self.tpatch(url, data=None, **kwargs)# PATCH
self.tput(url, data=None, **kwargs)  # PUT
self.tdelete(url, **kwargs)          # DELETE

# Ejemplos
response = self.tpost('/api/v1/clientes/', data={'nombre': 'Acme', ...})
response = self.tpatch(f'/api/v1/clientes/{uuid}/', data={'nombre': 'Nuevo'})
response = self.tdelete(f'/api/v1/clientes/{uuid}/')
```

---

## Assertion Helpers

```python
# Verifica status code + content-type: application/json
self.assertJSONResponse(response, status.HTTP_201_CREATED)
self.assertJSONResponse(response, status.HTTP_200_OK)
self.assertJSONResponse(response, status.HTTP_400_BAD_REQUEST)
self.assertJSONResponse(response, status.HTTP_409_CONFLICT)

# Verifica formato de paginación DRF
self.assertPaginationFormat(response.data)
# Equivale a:
#   self.assertIn('count', response.data)
#   self.assertIn('next', response.data)
#   self.assertIn('previous', response.data)
#   self.assertIn('results', response.data)

# Verifica aislamiento entre dos tenants
self.assertTenantIsolation(self.tenant, tenant2, ModelClass, create_func)
```

---

## `schema_context` — Cuándo Usarlo

```python
from django_tenants.utils import schema_context

# Para crear datos en un schema específico (ej: tenant2 en test de aislamiento)
with schema_context('public'):
    tenant2 = Client.objects.create(schema_name='tenant2_test', ...)

with schema_context(tenant2.schema_name):
    Empresa.objects.create(razon_social='Empresa 2', ...)

# NO necesario para setUp() normal — ya está dentro del schema del tenant principal
```

---

## Fixtures Requeridas por App

Algunas apps tienen prerequisitos que deben crearse en `setUp()`. Si faltan, el business service lanza `ValidationError` y los tests devuelven `400` en lugar de `201`.

### `empleados` — Devengos/Nómina
```python
import datetime
from apps.tenant.empleados.models import ResolucionDIAN
from apps.tenant.empresa.models import Empresa

empresa = Empresa.objects.first()
ResolucionDIAN.objects.create(
    empresa=empresa,
    numero_resolucion='TEST-001',
    rango_desde=1,
    rango_hasta=9999,
    fecha_resolucion=datetime.date(2023, 1, 1),
    fecha_inicio=datetime.date(2023, 1, 1),
    fecha_fin=datetime.date(2030, 12, 31),   # cubrir fecha_pago del test
    vigente=True,
    prefijo='NOM',
)
# consecutivo es auto-set a rango_desde (editable=False)
```

**Por qué:** `business_service.procesar_devengo()` valida que exista `ResolucionDIAN` con `vigente=True` y rango de fechas que contenga `fecha_pago`.

### `facturas` — Facturas de Venta
Puede requerir `ConfiguracionFactura` y `ResolucionDIAN` (misma clase). Verificar el business service.

### `contabilidad` — Asientos
No requiere fixtures especiales — el Pull Model extrae desde las apps origen.

### Apps sin prerequisitos especiales
`clientes`, `proveedores`, `gastos`, `inventario`, `cotizaciones`, `proyectos`, `bancos` — generalmente no requieren fixtures adicionales más allá del `Empresa` que ya crea la base.

---

## Estructura Estándar de Test por App

```python
import uuid
from django.test import override_settings
from rest_framework import status
from apps.config.tests.base_tenant import TenantAPITestCase
from apps.tenant.<app>.models import MiModelo
from apps.tenant.empresa.models import Empresa


@override_settings(ALLOWED_HOSTS=['*'])
class TestMiModeloAPI(TenantAPITestCase):

    def setUp(self):
        super().setUp()
        self.url_list = '/api/v1/<app>/<recurso>/'

        # 1. Crear fixtures de prerequisito si la app las necesita
        # (ver sección "Fixtures Requeridas por App")

        # 2. Payload de creación válido
        self.valid_payload = {
            'campo_a': 'valor',
            'campo_b': 'valor',
        }

    # --- CRUD mínimo ---

    def test_crear_exito(self):
        response = self.tpost(self.url_list, data=self.valid_payload)
        self.assertJSONResponse(response, status.HTTP_201_CREATED)
        self.assertIn('uuid', response.data)
        self.assertEqual(MiModelo.objects.count(), 1)

    def test_crear_duplicado_falla(self):
        self.tpost(self.url_list, data=self.valid_payload)
        response = self.tpost(self.url_list, data=self.valid_payload)
        self.assertJSONResponse(response, status.HTTP_400_BAD_REQUEST)

    def test_listar(self):
        self.tpost(self.url_list, data=self.valid_payload)
        response = self.tget(self.url_list)
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertPaginationFormat(response.data)
        self.assertEqual(response.data['count'], 1)

    def test_detalle(self):
        res = self.tpost(self.url_list, data=self.valid_payload)
        obj_uuid = res.data['uuid']
        response = self.tget(f'{self.url_list}{obj_uuid}/')
        self.assertJSONResponse(response, status.HTTP_200_OK)

    def test_actualizar(self):
        res = self.tpost(self.url_list, data=self.valid_payload)
        obj_uuid = res.data['uuid']
        response = self.tpatch(f'{self.url_list}{obj_uuid}/', data={'campo_a': 'nuevo'})
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertEqual(response.data['campo_a'], 'nuevo')

    def test_eliminar(self):
        res = self.tpost(self.url_list, data=self.valid_payload)
        obj_uuid = res.data['uuid']
        response = self.tdelete(f'{self.url_list}{obj_uuid}/')
        self.assertJSONResponse(response, status.HTTP_204_NO_CONTENT)
        self.assertEqual(MiModelo.objects.count(), 0)

    def test_uuid_read_only(self):
        res = self.tpost(self.url_list, data=self.valid_payload)
        obj_uuid = res.data['uuid']
        new_uuid = str(uuid.uuid4())
        response = self.tpatch(f'{self.url_list}{obj_uuid}/', data={'uuid': new_uuid})
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertNotEqual(response.data['uuid'], new_uuid)  # UUID no debe cambiar
```

---

## Comandos de Test

```bash
# Todos los tests
make test

# Un archivo específico
make test-file FILE="apps/tenant/empleados/tests/test_empleados_crud.py"

# Smoke tests
make smoke

# Directamente en Docker
docker compose exec web python -m pytest apps/tenant/<app>/tests/ -v
docker compose exec web python -m pytest apps/tenant/<app>/tests/test_<modelo>.py -v -k test_crear
```

---

## Anti-patrones Prohibidos

```python
# PROHIBIDO — self.empresa_id no existe en TenantAPITestCase
empresa_id = self.empresa_id   # AttributeError

# CORRECTO
empresa = Empresa.objects.first()

# PROHIBIDO — URL hardcoded con PK entero
url = f'/api/v1/empleados/{emp_id}/'   # BaseTenantViewSet usa UUID

# CORRECTO — usar uuid
url = f'/api/v1/empleados/{emp_uuid}/'

# PROHIBIDO — asumir que la app no tiene prerequisitos
# Verificar siempre el business service para entender qué valida antes de crear

# PROHIBIDO — olvidar @override_settings
class TestMiModeloAPI(TenantAPITestCase):  # sin @override_settings → 403/404 silencioso
    ...
```

---

## Registro de Conflictos Conocidos

| Status inesperado | Causa probable | Solución |
|---|---|---|
| `400` en vez de `201` | Fixture requerida faltante (ej: `ResolucionDIAN`) | Agregar fixture en `setUp()` |
| `403` en todos los tests | Falta `@override_settings(ALLOWED_HOSTS=['*'])` | Agregar decorator a la clase |
| `404` en endpoint existente | URL mal escrita o falta UUID vs PK | Verificar URL en `urls.py` y usar uuid |
| `500` en `setUp()` | Import circular o modelo no migrado | Verificar `make check-migrations` |
| Test pasa solo en orden alfab. | Estado compartido entre tests | Usar `setUp()` independiente, no variables de clase |
