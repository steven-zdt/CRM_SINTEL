# 🚀 Arquitectura API-First con DRF

**Versión:** 1.0  
**Fecha:** 2026-01-17  
**Estado:** ✅ IMPLEMENTADO

---

## 📋 Tabla de Contenidos

1. [Visión General](#visión-general)
2. [Estructura por App](#estructura-por-app)
3. [Configuración Global](#configuración-global)
4. [ViewSets y Routers](#viewsets-y-routers)
5. [Paginación](#paginación)
6. [Filtrado, Búsqueda y Ordenación](#filtrado-búsqueda-y-ordenación)
7. [Permisos](#permisos)
8. [Throttling](#throttling)
9. [Versionado](#versionado)
10. [OpenAPI Schema](#openapi-schema)
11. [Convenciones y Reglas](#convenciones-y-reglas)

---

## 🎯 Visión General

El proyecto SINTEL sigue una **arquitectura API-first** donde todas las funcionalidades están expuestas a través de APIs REST usando Django REST Framework (DRF).

### Principios

- **APIs REST como capa principal**: Todas las funcionalidades están expuestas a través de APIs REST
- **Frontend agnóstico**: El backend puede ser consumido por cualquier frontend (React, Vue, Angular, móvil, etc.)
- **Documentación automática**: APIs documentadas automáticamente con OpenAPI (drf-spectacular)
- **Versionado de APIs**: Capacidad de versionar APIs para mantener compatibilidad
- **Integración fácil**: Facilita la integración con sistemas externos y terceros

### Endpoints Principales

- **APIs por tenant**: `http://tenant.localhost:8000/api/v1/`
- **APIs públicas**: `http://localhost:8000/api/public/v1/`
- **OpenAPI Schema**: `http://localhost:8000/api/schema/`
- **Swagger UI**: `http://localhost:8000/api/docs/`
- **ReDoc**: `http://localhost:8000/api/redoc/`

---

## 📁 Estructura por App

Cada app (tanto en `apps/public/*` como `apps/tenant/*`) debe tener una carpeta `api/` con la siguiente estructura:

```
apps/
├── public/
│   ├── accounts/
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── serializers.py      # Serializers para todos los modelos
│   │       ├── viewsets.py          # ViewSets (ModelViewSet o ReadOnlyModelViewSet)
│   │       ├── permissions.py       # Permisos personalizados (opcional)
│   │       ├── filters.py           # Filtros personalizados (opcional)
│   │       ├── pagination.py        # Paginación personalizada (opcional)
│   │       └── urls.py              # Router y registro de ViewSets
│   └── impuestos/
│       └── api/                     # Misma estructura
└── tenant/
    ├── empresa/
    │   └── api/                     # Misma estructura
    ├── facturas/
    │   └── api/                     # Misma estructura
    └── contabilidad/
        └── api/                     # Misma estructura
```

### Archivos Mínimos Requeridos

1. **`api/__init__.py`**: Documentación del módulo API
2. **`api/serializers.py`**: Un `ModelSerializer` por cada modelo concreto
3. **`api/viewsets.py`**: ViewSets con lista `VIEWSETS` para registro automático
4. **`api/urls.py`**: Router que registra automáticamente todos los ViewSets

### Archivos Opcionales

- **`api/permissions.py`**: Permisos personalizados (por defecto usa `apps.config.api.permissions`)
- **`api/filters.py`**: Filtros personalizados (si necesitas más que `filterset_fields`)
- **`api/pagination.py`**: Paginación personalizada (por defecto usa `StandardResultsSetPagination`)

---

## ⚙️ Configuración Global

La configuración global de DRF está en `config/settings.py`:

```python
REST_FRAMEWORK = {
    # OpenAPI Schema (drf-spectacular)
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    
    # Autenticación
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    
    # Permisos (por defecto: IsAuthenticated)
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    
    # Filtrado, búsqueda y ordenación
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    
    # Paginación global
    'DEFAULT_PAGINATION_CLASS': 'apps.config.api.pagination.StandardResultsSetPagination',
    'PAGE_SIZE': 25,
    
    # Throttling
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day',
    },
    
    # Versionado
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.NamespaceVersioning',
}
```

### Módulo Compartido: `apps/config/api/`

Contiene configuración compartida para todas las APIs:

- **`pagination.py`**: `StandardResultsSetPagination` (page_size=25, max_page_size=100)
- **`permissions.py`**: Permisos base y `IsTenantAdmin` (ejemplo)
- **`exceptions.py`**: Handler personalizado de excepciones (opcional)

---

## 🔄 ViewSets y Routers

### Tipos de ViewSets

1. **`ModelViewSet`**: CRUD completo (Create, Read, Update, Delete)
   - Usar para modelos de negocio (empresa, facturas, contabilidad)
   
2. **`ReadOnlyModelViewSet`**: Solo lectura (Read)
   - Usar para catálogos (impuestos/DIAN)

### Ejemplo de ViewSet

```python
from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from apps.tenant.empresa.models import Empresa
from apps.tenant.empresa.api.serializers import EmpresaSerializer
from apps.config.api.pagination import StandardResultsSetPagination

class EmpresaViewSet(viewsets.ModelViewSet):
    """ViewSet para Empresa."""
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    
    # Filtros simples
    filterset_fields = ['activa', 'ciudad', 'departamento']
    
    # Búsqueda (campos textuales)
    search_fields = ['razon_social', 'nombre_comercial', 'nit', 'email']
    
    # Ordenación
    ordering_fields = ['razon_social', 'nit', 'created_at', 'updated_at']
    ordering = ['razon_social']

# Lista para registro automático
VIEWSETS = [
    (r'empresas', EmpresaViewSet, 'empresa'),
]
```

### Registro Automático en Router

En `api/urls.py`:

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.tenant.empresa.api.viewsets import VIEWSETS

router = DefaultRouter()

# Registrar automáticamente
for prefix, viewset, basename in VIEWSETS:
    router.register(prefix, viewset, basename=basename)

urlpatterns = [
    path('', include(router.urls)),
]
```

### Referencias

- [DRF ViewSets](https://www.django-rest-framework.org/api-guide/viewsets/)
- [DRF Routers](https://www.django-rest-framework.org/api-guide/routers/)

---

## 📄 Paginación

### Paginación Global

- **Clase**: `StandardResultsSetPagination` (en `apps/config/api/pagination.py`)
- **Tamaño por defecto**: 25 resultados por página
- **Parámetro**: `?page_size=50` (máximo 100)
- **Parámetro de página**: `?page=2`

### Override por ViewSet

```python
from apps.config.api.pagination import StandardResultsSetPagination

class MiViewSet(viewsets.ModelViewSet):
    pagination_class = StandardResultsSetPagination  # Por defecto
    # O crear una clase personalizada si necesitas otro comportamiento
```

### Referencias

- [DRF Pagination](https://www.django-rest-framework.org/api-guide/pagination/)

---

## 🔍 Filtrado, Búsqueda y Ordenación

### Filtrado Simple (`filterset_fields`)

Para filtros simples (igualdad exacta):

```python
filterset_fields = ['activa', 'ciudad', 'departamento', 'estado']
```

Uso: `?activa=true&ciudad=Bogotá`

### Búsqueda (`search_fields`)

Para búsqueda textual (LIKE):

```python
search_fields = ['razon_social', 'nombre_comercial', 'nit', 'email']
```

Uso: `?search=empresa`

### Ordenación (`ordering_fields`)

Para ordenar resultados:

```python
ordering_fields = ['razon_social', 'nit', 'created_at', 'updated_at']
ordering = ['razon_social']  # Orden por defecto
```

Uso: `?ordering=-created_at` (descendente) o `?ordering=razon_social` (ascendente)

### Filtros Personalizados (`FilterSet`)

Si necesitas filtros más complejos, crea un `FilterSet` en `api/filters.py`:

```python
import django_filters
from apps.tenant.empresa.models import Empresa

class EmpresaFilter(django_filters.FilterSet):
    razon_social_icontains = django_filters.CharFilter(
        field_name='razon_social',
        lookup_expr='icontains'
    )
    
    class Meta:
        model = Empresa
        fields = ['activa', 'ciudad']
```

Luego en el ViewSet:

```python
from apps.tenant.empresa.api.filters import EmpresaFilter

class EmpresaViewSet(viewsets.ModelViewSet):
    filterset_class = EmpresaFilter  # En lugar de filterset_fields
```

### Referencias

- [django-filter](https://django-filter.readthedocs.io/)
- [DRF Filtering](https://www.django-rest-framework.org/api-guide/filtering/)

---

## 🔐 Permisos

### Permisos por Defecto

- **Global**: `IsAuthenticated` (requiere autenticación)
- **Por ViewSet**: Se puede sobrescribir con `permission_classes`

### Ejemplos

```python
# Solo autenticados
permission_classes = [permissions.IsAuthenticated]

# Solo administradores
permission_classes = [permissions.IsAdminUser]

# Público (sin autenticación)
permission_classes = [permissions.AllowAny]

# Personalizado
permission_classes = [IsTenantAdmin]  # Desde apps.config.api.permissions
```

### Referencias

- [DRF Permissions](https://www.django-rest-framework.org/api-guide/permissions/)

---

## ⏱️ Throttling

### Throttling Global

- **Anónimos**: 100 requests/día
- **Autenticados**: 1000 requests/día

### Override por ViewSet

```python
from rest_framework.throttling import ScopedRateThrottle

class MiViewSet(viewsets.ModelViewSet):
    throttle_scope = 'custom_scope'
    throttle_classes = [ScopedRateThrottle]
```

Y en `settings.py`:

```python
'DEFAULT_THROTTLE_RATES': {
    'anon': '100/day',
    'user': '1000/day',
    'custom_scope': '500/hour',  # Throttling personalizado
}
```

### Referencias

- [DRF Throttling](https://www.django-rest-framework.org/api-guide/throttling/)

---

## 🔢 Versionado

### Configuración Actual

- **Clase**: `NamespaceVersioning`
- **Versión actual**: `v1`
- **URLs**: `/api/v1/`, `/api/v2/` (futuro)

### Uso en Código

```python
def mi_vista(request):
    version = request.version  # 'v1', 'v2', etc.
    if version == 'v2':
        # Lógica para v2
        pass
```

### Extensión a v2

Para agregar v2 en el futuro:

1. Crear `config/api_urls_v2.py`
2. En `config/urls.py`:
   ```python
   path('api/v2/', include(('config.api_urls_v2', 'api'), namespace='v2')),
   ```

### Referencias

- [DRF Versioning](https://www.django-rest-framework.org/api-guide/versioning/)

---

## 📖 OpenAPI Schema

### drf-spectacular

El proyecto usa **drf-spectacular** (recomendado por DRF) para generar el esquema OpenAPI.

### Endpoints

- **Schema JSON/YAML**: `http://localhost:8000/api/schema/`
- **Swagger UI**: `http://localhost:8000/api/docs/`
- **ReDoc**: `http://localhost:8000/api/redoc/`

### Comandos

```bash
# Validar esquema
make api-check

# Generar esquema
make api-schema
```

### Referencias

- [drf-spectacular](https://drf-spectacular.readthedocs.io/)
- [DRF Schemas deprecation](https://www.django-rest-framework.org/api-guide/schemas/)

---

## 📐 Convenciones y Reglas

### Regla 1: Estructura por App

✅ **CORRECTO**: Cada app tiene su carpeta `api/` con los módulos mínimos  
❌ **INCORRECTO**: ViewSets en `views.py` sin estructura `api/`

### Regla 2: Registro Automático

✅ **CORRECTO**: Usar lista `VIEWSETS` en `viewsets.py` y registro automático en `urls.py`  
❌ **INCORRECTO**: Registrar ViewSets manualmente en `config/api_urls.py`

### Regla 3: Paginación

✅ **CORRECTO**: Usar `StandardResultsSetPagination` por defecto  
❌ **INCORRECTO**: Crear paginación personalizada sin necesidad

### Regla 4: Filtrado/Búsqueda/Ordenación

✅ **CORRECTO**: Declarar `filterset_fields`, `search_fields`, `ordering_fields` en ViewSet  
❌ **INCORRECTO**: Filtrar manualmente en `get_queryset()` sin usar los backends

### Regla 5: Permisos

✅ **CORRECTO**: `IsAuthenticated` por defecto, `AllowAny` explícito para públicos  
❌ **INCORRECTO**: APIs públicas sin declarar `AllowAny` explícitamente

### Regla 6: Versionado

✅ **CORRECTO**: Todas las rutas bajo `/api/v{N}/` y versionadas por namespace  
❌ **INCORRECTO**: APIs sin versionar o versionadas manualmente

### Regla 7: OpenAPI Schema

✅ **CORRECTO**: El esquema debe buildar sin warnings (`spectacular --validate`)  
❌ **INCORRECTO**: Warnings en la generación del esquema

---

## 📚 Referencias Externas

- [DRF ViewSets & Routers](https://www.django-rest-framework.org/api-guide/viewsets/)
- [DRF Pagination](https://www.django-rest-framework.org/api-guide/pagination/)
- [django-filter](https://django-filter.readthedocs.io/)
- [DRF Filtering](https://www.django-rest-framework.org/api-guide/filtering/)
- [DRF Permissions](https://www.django-rest-framework.org/api-guide/permissions/)
- [DRF Throttling](https://www.django-rest-framework.org/api-guide/throttling/)
- [DRF Versioning](https://www.django-rest-framework.org/api-guide/versioning/)
- [drf-spectacular](https://drf-spectacular.readthedocs.io/)

---

**Última Actualización:** 2026-01-17
