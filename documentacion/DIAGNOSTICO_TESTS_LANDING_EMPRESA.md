# Diagnóstico: Problema en Tests de Landing Empresa

## 🔍 Problema Identificado

**Ubicación del Error:**
- Archivo: `tests/tenant/landing/test_landing_empresa.py`
- Línea: 71 (en `test_api_empresa_publica_sin_autenticacion`)
- Error: `404 Not Found` cuando se intenta acceder a `/api/v1/landing/empresa/`

## 📊 Análisis Comparativo

### Tests que FUNCIONAN (test_landing_architecture.py)

```python
# Línea 54: Cambiar esquema
connection.set_schema(tenant.schema_name)

# Línea 58: Hacer request SIN override_settings
api_client = APIClient()
response = api_client.get('/api/v1/landing/info/')  # ✅ FUNCIONA
```

**Características:**
- ✅ NO usa `override_settings(ROOT_URLCONF='config.urls_tenant')`
- ✅ URL: `/api/v1/landing/info/` (registrada en router con `@action`)
- ✅ ViewSet: `LandingViewSet` con método `info()` decorado con `@action`

### Tests que FALLAN (test_landing_empresa.py)

```python
# Línea 53: Cambiar esquema
connection.set_schema('test_empresa_api')

# Línea 69-71: Hacer request CON override_settings
with override_settings(ROOT_URLCONF='config.urls_tenant'):
    api_client = APIClient()
    response = api_client.get('/api/v1/landing/empresa/')  # ❌ 404 NOT FOUND
```

**Características:**
- ❌ Usa `override_settings(ROOT_URLCONF='config.urls_tenant')` (pero aún falla)
- ❌ URL: `/api/v1/landing/empresa/` (registrada como `path` manual)
- ❌ ViewSet: `LandingInfoViewSet` con método `list()` (no `@action`)

## 🎯 Causa Raíz Identificada

### Problema Principal: `TenantMainMiddleware` no se ejecuta en tests

**Explicación:**
1. En producción/desarrollo, el `TenantMainMiddleware` (línea 85 de `config/settings.py`) es el que:
   - Detecta el tenant según el dominio
   - Cambia `ROOT_URLCONF` de `config.urls_public` a `config.urls_tenant`
   - Establece el esquema de base de datos

2. En los tests:
   - El middleware **NO se ejecuta automáticamente**
   - `connection.set_schema()` solo cambia el esquema de DB, **NO cambia ROOT_URLCONF**
   - `override_settings(ROOT_URLCONF='config.urls_tenant')` debería funcionar, pero parece que no se aplica correctamente

### Diferencia Clave: Router vs Path Manual

**Tests que funcionan:**
- Usan URLs generadas por `DefaultRouter` de DRF
- El router registra automáticamente las rutas con `@action`
- Ejemplo: `/api/v1/landing/info/` → `LandingViewSet.info()` (vía router)

**Tests que fallan:**
- Usan URLs registradas manualmente con `path()`
- La URL está en `apps/tenant/landing/api/urls.py` línea 24:
  ```python
  path('empresa/', LandingInfoViewSet.as_view({'get': 'list'}), name='landing-empresa'),
  ```
- Esta URL depende de que `ROOT_URLCONF` esté configurado correctamente

## 🔧 Punto Exacto del Problema

**Archivo:** `tests/tenant/landing/test_landing_empresa.py`
**Línea:** 69-71
**Código:**
```python
with override_settings(ROOT_URLCONF='config.urls_tenant'):
    api_client = APIClient()
    response = api_client.get('/api/v1/landing/empresa/')  # ❌ 404
```

**Motivo del 404:**
1. `override_settings` no está recargando correctamente las URLs
2. Django sigue usando `ROOT_URLCONF = 'config.urls_public'` (por defecto)
3. La URL `/api/v1/landing/empresa/` NO existe en `config.urls_public`
4. Solo existe en `config.urls_tenant` (línea 60 de `config/urls_tenant.py`)

## 💡 Soluciones Posibles

### Opción 1: Usar el mismo patrón que los tests que funcionan
Eliminar `override_settings` y confiar en que el middleware se ejecute (pero esto no funciona porque el middleware no se ejecuta en tests).

### Opción 2: Forzar recarga de URLs después de override_settings
```python
from django.urls import clear_url_caches
with override_settings(ROOT_URLCONF='config.urls_tenant'):
    clear_url_caches()  # Recargar caché de URLs
    api_client = APIClient()
    response = api_client.get('/api/v1/landing/empresa/')
```

### Opción 3: Registrar la URL en el router (como `/info/`)
Cambiar `LandingInfoViewSet` para usar `@action` en lugar de `path` manual:
```python
# En LandingInfoViewSet
@action(detail=False, methods=['get'], url_path='empresa', url_name='empresa')
def empresa(self, request):
    return self.retrieve(request, pk=None)
```

### Opción 4: Usar RequestFactory con URLconf explícito
```python
from django.test import RequestFactory
from django.urls import set_urlconf

set_urlconf('config.urls_tenant')
factory = RequestFactory()
request = factory.get('/api/v1/landing/empresa/')
```

## ✅ Recomendación

**Solución Recomendada: Opción 3** (usar `@action` en el router)

**Razón:**
- Es consistente con el patrón que ya funciona (`/api/v1/landing/info/`)
- No requiere `override_settings` ni recarga de caché
- Sigue el estándar API-First del proyecto
- Los tests existentes ya validan este patrón

**Implementación:**
1. Mover la lógica de `LandingInfoViewSet.list()` a un método `empresa()` con `@action`
2. Registrar `LandingInfoViewSet` en el router
3. Eliminar el `path` manual de `apps/tenant/landing/api/urls.py`
4. Actualizar los tests para eliminar `override_settings`
