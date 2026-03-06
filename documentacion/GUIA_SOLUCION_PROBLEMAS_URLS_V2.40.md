# 🔧 Guía de Solución de Problemas Comunes - URLs y Arquitectura Multi-Tenant v2.40

**Versión:** 2.40  
**Última Actualización:** 2026-02-15  
**Estado:** ✅ Documentación completa de problemas resueltos

---

## 📋 Tabla de Contenidos

1. [Problema: ImportError en services/__init__.py](#problema-1-importerror-en-services__init__py)
2. [Problema: AttributeError 'User' object has no attribute 'empresa'](#problema-2-attributeerror-user-object-has-no-attribute-empresa)
3. [Problema: 404 en endpoints de API](#problema-3-404-en-endpoints-de-api)
4. [Problema: TypeError en GET requests con body](#problema-4-typeerror-en-get-requests-con-body)
5. [Checklist para Nuevas Apps](#checklist-para-nuevas-apps)

---

## Problema 1: ImportError en services/__init__.py

### Síntoma

```
AttributeError: module 'apps.tenant.{app}.services_module_init' has no attribute 'DETAIL_FIELDS'
ModuleNotFoundError: No module named 'apps.tenant.{app}.services.services'
```

### Causa Raíz

**Conflicto de Nombres:** Cuando existe tanto un **paquete** `services/` (con `__init__.py`) como un **archivo** `services.py` en el mismo directorio, Python puede confundirse al importar.

```
apps/tenant/{app}/
├── services/          # ⚠️ Paquete (directorio con __init__.py)
│   └── __init__.py
└── services.py        # ⚠️ Archivo (conflicto de nombres)
```

### Solución

Usar `importlib` para cargar directamente el archivo `services.py`, evitando que Python intente cargar el paquete primero.

**Patrón Correcto (`apps/tenant/{app}/services/__init__.py`):**

```python
"""
Service Layer para {app} - Re-exporta símbolos de services.py para importación limpia.

⚠️ v2.40: Arquitectura simplificada con importaciones estándar de Django.
Re-exporta todas las funciones del service layer para uso en ViewSets y Serializers.

⚠️ CRÍTICO: Este archivo está en apps/tenant/{app}/services/__init__.py
El archivo services.py está en apps/tenant/{app}/services.py (nivel superior).

PROBLEMA DE CIRCULARIDAD:
- Existe un paquete services/ (con este __init__.py)
- Existe un archivo services.py (nivel superior)
- Python confunde ambos al hacer `from apps.tenant.{app}.services import ...`

SOLUCIÓN:
- Usar importlib para cargar directamente el archivo services.py
- Esto evita que Python intente cargar el paquete services/ primero
- Las funciones se re-exportan explícitamente para uso en ViewSets
"""
# ⚠️ v2.40: Importación directa desde el archivo services.py para evitar circularidad
import importlib.util
from pathlib import Path

# Ruta al archivo services.py (nivel superior del paquete {app})
services_py_path = Path(__file__).resolve().parent.parent / 'services.py'

if services_py_path.exists():
    # Cargar el módulo directamente desde el archivo
    spec = importlib.util.spec_from_file_location('apps.tenant.{app}.services_module', services_py_path)
    services_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(services_module)
    
    # Re-exportar todas las funciones requeridas
    LIST_FIELDS = services_module.LIST_FIELDS
    qs_list = services_module.qs_list
    get_summary = services_module.get_summary
    # ... otras funciones necesarias
    
else:
    raise ImportError(f"No se encontró el archivo services.py en {services_py_path.parent}")

# ⚠️ v2.40: Exportar explícitamente todas las funciones requeridas
__all__ = [
    'LIST_FIELDS',
    'qs_list',
    'get_summary',
    # ... otras funciones
]
```

### Ejemplo Real: `apps/tenant/empleados/services/__init__.py`

```python
import importlib.util
from pathlib import Path

services_py_path = Path(__file__).resolve().parent.parent / 'services.py'

if services_py_path.exists():
    spec = importlib.util.spec_from_file_location('apps.tenant.empleados.services_module', services_py_path)
    services_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(services_module)
    
    LIST_FIELDS = services_module.LIST_FIELDS
    qs_empleados_list = services_module.qs_empleados_list
    get_nomina_summary = services_module.get_nomina_summary
    anular_devengo_service = services_module.anular_devengo_service
else:
    raise ImportError(f"No se encontró el archivo services.py en {services_py_path.parent}")

__all__ = [
    'LIST_FIELDS',
    'qs_empleados_list',
    'get_nomina_summary',
    'anular_devengo_service',
]
```

---

## Problema 2: AttributeError 'User' object has no attribute 'empresa'

### Síntoma

```
AttributeError: 'User' object has no attribute 'empresa'
File "/app/apps/tenant/{app}/api/viewsets.py", line 83, in get_queryset
    empresa = self.request.user.empresa
```

### Causa Raíz

**Arquitectura Multi-Tenant:** En `django-tenants`:
- `User` está en el esquema `public` (SHARED_APPS)
- `Empresa` está en el esquema del tenant (TENANT_APPS)
- **NO hay relación directa** entre `User` y `Empresa` porque están en esquemas diferentes
- La empresa se obtiene como **singleton del tenant actual**, no desde el usuario

### Solución

**Patrón Correcto:** Obtener la empresa como singleton del tenant actual usando `Empresa.objects.first()`.

**❌ INCORRECTO:**

```python
def get_queryset(self):
    empresa = self.request.user.empresa  # ⚠️ AttributeError
    return Modelo.objects.filter(empresa=empresa)
```

**✅ CORRECTO:**

```python
def get_queryset(self):
    """
    ⚠️ MULTI-TENANT: La empresa se obtiene como singleton del tenant actual.
    No hay relación directa entre User (public) y Empresa (tenant).
    """
    from apps.tenant.empresa.models import Empresa
    empresa = Empresa.objects.first()  # Singleton: solo una empresa por tenant
    
    if not empresa:
        return Modelo.objects.none()
    
    return Modelo.objects.filter(empresa=empresa)
```

### Ejemplo Completo: ViewSet Corregido

```python
from apps.tenant.empresa.models import Empresa

class MiViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        """SSoT: Siempre filtrar por la empresa del tenant actual."""
        empresa = Empresa.objects.first()  # Singleton del tenant
        if not empresa:
            return MiModelo.objects.none()
        return MiModelo.objects.filter(empresa=empresa)
    
    def perform_create(self, serializer):
        """Asignación automática de empresa al crear (SSoT)."""
        empresa = Empresa.objects.first()
        if not empresa:
            raise ValueError("No se encontró empresa configurada para este tenant")
        serializer.save(empresa=empresa)
    
    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """Endpoint de resumen."""
        empresa = Empresa.objects.first()
        if not empresa:
            return Response(
                {"error": "empresa_no_configurada", "message": "No se encontró empresa configurada"},
                status=status.HTTP_404_NOT_FOUND
            )
        data = get_summary(empresa)
        return Response(data, status=status.HTTP_200_OK)
```

---

## Problema 3: 404 en Endpoints de API

### Síntoma

```
GET /api/v1/{app}/ 404 (Not Found)
GET /api/v1/{app}/summary/ 404 (Not Found)
```

### Causa Raíz

1. **Router no registrado correctamente** en `apps/tenant/{app}/api/urls.py`
2. **URLs no incluidas** en `config/api_urls.py`
3. **Error de importación** que impide cargar el ViewSet

### Solución

#### Paso 1: Configurar Router Correctamente

**Patrón Correcto (`apps/tenant/{app}/api/urls.py`):**

```python
"""
URLs de la API de {app} (DRF Router).

⚠️ v2.40: Arquitectura API-First con DefaultRouter.
- Todas las rutas están bajo /api/v1/{app}/ (configurado en config/api_urls.py)
- Usa DefaultRouter para generar endpoints automáticamente
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
import logging

logger = logging.getLogger(__name__)

try:
    from .viewsets import MiViewSet
except ImportError as e:
    logger.error(f"❌ ERROR: No se pudo importar ViewSet: {e}", exc_info=True)
    raise

# ⚠️ RECONSTRUCCIÓN COMPLETA DEL ROUTER (v2.40)
router = DefaultRouter()

# ⚠️ CRÍTICO: Registro en la raíz (string vacío) porque el prefijo '{app}/' ya está en config/api_urls.py
# El basename '{app}' es VITAL para que DRF genere las URLs correctamente
try:
    router.register(r'', MiViewSet, basename='{app}')
    logger.info("✅ ViewSet registrado correctamente en router")
except Exception as e:
    logger.error(f"❌ ERROR registrando ViewSet en router: {e}", exc_info=True)
    raise

# URLs generadas por el router
# ⚠️ ESTRUCTURA EXPLÍCITA: Usar router.urls directamente (patrón estándar DRF)
urlpatterns = router.urls

# Log de URLs generadas (solo en DEBUG)
import django.conf
if django.conf.settings.DEBUG:
    logger.debug(f"📋 URLs de {app} generadas: {[str(url.pattern) for url in router.urls]}")
```

#### Paso 2: Incluir URLs en config/api_urls.py

**Patrón Correcto (`config/api_urls.py`):**

```python
try:
    urlpatterns.append(path('{app}/', include('apps.tenant.{app}.api.urls')))
    logger.info("✅ URLs de {app} registradas correctamente: /api/v1/{app}/")
except (ImportError, AttributeError) as e:
    logger.error(f"❌ ERROR: No se pudieron cargar URLs de {app}: {e}", exc_info=True)
except Exception as e:
    logger.error(f"❌ ERROR INESPERADO cargando URLs de {app}: {e}", exc_info=True)
```

#### Paso 3: Verificar que el ViewSet se Importa Correctamente

**Verificación:**

```bash
python manage.py shell
>>> from apps.tenant.{app}.api.urls import router
>>> print([str(url.pattern) for url in router.urls])
```

Debería mostrar las URLs generadas sin errores.

---

## Problema 4: TypeError en GET Requests con Body

### Síntoma

```
TypeError: Failed to execute 'fetch' on 'Window': Request with GET/HEAD method cannot have body
```

### Causa Raíz

**Protocolo HTTP:** Los métodos GET/HEAD **NO pueden tener body**. Los parámetros deben ir en la **query string** (URL).

### Solución

**❌ INCORRECTO (JavaScript):**

```javascript
// ⚠️ ERROR: GET con body
w.http('GET', '/api/v1/app/', { page: 1, limit: 10 })
```

**✅ CORRECTO (JavaScript):**

```javascript
/**
 * Construye URL con query parameters para GET requests
 * ⚠️ v2.40: NUNCA enviar body en GET requests
 */
function buildUrlWithParams(baseUrl, params = {}) {
    if (!params || Object.keys(params).length === 0) {
        return baseUrl;
    }
    
    const url = new URL(baseUrl, window.location.origin);
    Object.keys(params).forEach(key => {
        const value = params[key];
        if (value !== null && value !== undefined && value !== '') {
            url.searchParams.append(key, String(value));
        }
    });
    
    return url.pathname + url.search;
}

// Uso correcto
w.appAPI = {
    list: (params = {}) => {
        const url = buildUrlWithParams(`${API_BASE}/`, params);
        return w.http('GET', url);  // ⚠️ Sin body
    },
    
    getSummary: () => {
        return w.http('GET', `${API_BASE}/summary/`);  // ⚠️ Sin body
    }
};
```

---

## Checklist para Nuevas Apps

### ✅ Configuración de URLs

- [ ] Router registrado con `r''` (string vacío) en `apps/tenant/{app}/api/urls.py`
- [ ] Basename correcto: `router.register(r'', ViewSet, basename='{app}')`
- [ ] URLs incluidas en `config/api_urls.py` con logging
- [ ] ViewSet se importa sin errores

### ✅ Service Layer

- [ ] Si existe `services/` y `services.py`, usar `importlib` en `services/__init__.py`
- [ ] Funciones re-exportadas explícitamente en `__all__`
- [ ] `LIST_FIELDS` y `DETAIL_FIELDS` definidos si aplica

### ✅ Multi-Tenant

- [ ] **NUNCA** usar `request.user.empresa` (AttributeError)
- [ ] **SIEMPRE** usar `Empresa.objects.first()` para obtener empresa
- [ ] Validar que empresa existe antes de usarla
- [ ] Filtrar querysets por `empresa` (SSoT)

### ✅ Frontend (JavaScript)

- [ ] GET requests **NO** envían body
- [ ] Usar `buildUrlWithParams()` para query strings
- [ ] URLs correctas: `/api/v1/{app}/` (sin doble prefijo)
- [ ] Manejo de errores con funciones locales (no depender de helpers globales)

### ✅ ViewSet

- [ ] `get_queryset()` obtiene empresa con `Empresa.objects.first()`
- [ ] `perform_create()` asigna empresa automáticamente
- [ ] Acciones `@action` obtienen empresa correctamente
- [ ] Manejo de errores cuando empresa no existe

---

## 📚 Referencias

- **Arquitectura General:** `documentacion/arquitectura_general.md`
- **Ejemplo Funcional:** `apps/tenant/empleados/` (corregido v2.40)
- **Ejemplo Funcional:** `apps/tenant/gastos/` (corregido v2.40)

---

## 🔍 Verificación Rápida

```bash
# 1. Verificar que el router genera URLs
python manage.py shell
>>> from apps.tenant.{app}.api.urls import router
>>> [str(url.pattern) for url in router.urls]

# 2. Verificar que no hay errores de importación
python manage.py check

# 3. Verificar que las URLs están registradas
python manage.py show_urls | grep {app}
```

---

**Última Actualización:** 2026-02-15  
**Mantenido por:** Equipo de Desarrollo SINTEL
