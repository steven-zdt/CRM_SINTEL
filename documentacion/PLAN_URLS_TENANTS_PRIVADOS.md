# Plan de URLs para Tenants Privados - v2.61

**Fecha:** 2024-12-19  
**Estado:** ✅ Validado y Planificado  
**Referencia:** `documentacion/arquitectura_general.md`

---

## 📋 Resumen Ejecutivo

Este documento valida la lógica de URLs para tenants privados y propone un plan de implementación para corregir el endpoint de login faltante en Core API.

### Problema Identificado

- **Error:** `POST /api/v1/core/auth/login/` retorna 404
- **Causa:** El endpoint está documentado pero no implementado en Core API
- **Impacto:** El frontend no puede autenticar usuarios en tenants privados
- **Estado Actual:** Existe un endpoint alternativo en Landing API (`/api/v1/landing/auth/login/`)

---

## 🏗️ Arquitectura de URLs para Tenants Privados

### Estructura Actual (TENANT_URLCONF)

**Archivo:** `config/urls_tenant.py`  
**Se activa cuando:** Se accede a un dominio de tenant privado (ej: `cliente.sintel.com`)

```python
# Estructura de urlpatterns en config/urls_tenant.py

urlpatterns = [
    # 1. Ruta Raíz
    path('', TenantRootView.as_view(), name='tenant_root'),
    
    # 2. Shells Estáticos (UI)
    path('activate/', ...),
    path('login/', ...),
    path('dashboard/', ...),
    path('empresa/', ...),
    path('facturas/', ...),
    path('contabilidad/', ...),
    
    # 3. APIs REST del Tenant
    path('api/v1/', include('config.api_urls')),  # ← Incluye Core API aquí
    path('api/v1/landing/', include('apps.tenant.landing.api.urls')),
    
    # 4. UI Routes (partials HTML)
    path('', include('apps.tenant.core.urls_ui')),
    path('ui/landing/', include('apps.tenant.landing.urls_ui')),
    path('ui/dashboard/', include('apps.tenant.dashboard.urls_ui')),
    
    # 5. JWT Auth
    path('api/token/', TokenObtainPairView.as_view()),
    path('api/token/refresh/', TokenRefreshView.as_view()),
    path('api/token/verify/', LoggedTokenVerifyView.as_view()),
]
```

### Flujo de Resolución de URLs

```
cliente.sintel.com/api/v1/core/auth/login/
  ↓
TenantMainMiddleware (identifica tenant)
  ↓
TENANT_URLCONF = 'config.urls_tenant'
  ↓
path('api/v1/', include('config.api_urls'))
  ↓
config/api_urls.py
  ↓
path('core/', include('apps.tenant.core.api.urls'))
  ↓
apps/tenant/core/api/urls.py
  ↓
❌ router.register(r"auth", CoreAuthViewSet)  # ← NO EXISTE
```

---

## 📊 Plan de URLs para Tenants Privados

### 1. APIs REST Centralizadas (Core API)

**Ubicación:** `apps/tenant/core/api/urls.py`  
**Prefijo:** `/api/v1/core/`

#### 1.1 Autenticación (Auth) - ⚠️ FALTANTE

| Endpoint | Método | Vista | Estado |
|----------|--------|-------|--------|
| `/api/v1/core/auth/login/` | POST | `CoreAuthViewSet.login` | ✅ **IMPLEMENTADO v2.61** |
| `/api/v1/core/auth/logout/` | POST | `CoreAuthViewSet.logout` | ✅ **IMPLEMENTADO v2.61** |
| `/api/v1/core/auth/password-reset/request/` | POST | `PasswordResetRequestView` | ❌ **NO IMPLEMENTADO** |
| `/api/v1/core/auth/password-reset/validate/` | POST | `PasswordResetValidateView` | ❌ **NO IMPLEMENTADO** |
| `/api/v1/core/auth/password-reset/confirm/` | POST | `PasswordResetConfirmView` | ❌ **NO IMPLEMENTADO** |

**Alternativa Actual (Landing API):**
- ✅ `/api/v1/landing/auth/login/` → `TenantLoginAPIView` (funciona)
- ✅ `/api/v1/landing/auth/logout/` → `TenantLogoutAPIView` (funciona)

#### 1.2 Landing (Resumen)

| Endpoint | Método | Vista | Estado |
|----------|--------|-------|--------|
| `/api/v1/core/landing/resumen/` | GET | `LandingResumenView` | ✅ Implementado |

#### 1.3 Dashboard (Secciones)

| Endpoint | Método | Vista | Estado |
|----------|--------|-------|--------|
| `/api/v1/core/dashboard/sections/` | GET | `DashboardSectionsViewSet` | ✅ Implementado |

#### 1.4 Links (Registro de Rutas)

| Endpoint | Método | Vista | Estado |
|----------|--------|-------|--------|
| `/api/v1/core/links/` | GET | `CoreLinksViewSet` | ✅ Implementado |

### 2. APIs REST por App

**Ubicación:** `config/api_urls.py`  
**Prefijo:** `/api/v1/{app}/`

| App | Endpoints | Estado |
|-----|-----------|--------|
| `contabilidad` | `/api/v1/contabilidad/cuentas-contables/`, `/api/v1/contabilidad/asientos-contables/`, etc. | ✅ Implementado |
| `facturas` | `/api/v1/facturas/` | ✅ Implementado |
| `empresa` | `/api/v1/empresas/` | ✅ Implementado |
| `clientes` | `/api/v1/clientes/` | ✅ Implementado |
| `proveedores` | `/api/v1/proveedores/` | ✅ Implementado |
| `gastos` | `/api/v1/gastos/` | ✅ Implementado |
| `empleados` | `/api/v1/empleados/` | ✅ Implementado |
| `inventario` | `/api/v1/inventario/` | ✅ Implementado |
| `cotizaciones` | `/api/v1/cotizaciones/` | ✅ Implementado |

### 3. Landing API (Legacy/Alternativa)

**Ubicación:** `apps/tenant/landing/api/urls.py`  
**Prefijo:** `/api/v1/landing/`

| Endpoint | Método | Vista | Estado |
|----------|--------|-------|--------|
| `/api/v1/landing/info/` | GET | `LandingViewSet.info` | ✅ Implementado |
| `/api/v1/landing/auth/login/` | POST | `LandingViewSet.login` | ✅ Implementado (alternativa) |
| `/api/v1/landing/auth/activate/` | GET/POST | `LandingViewSet.activate` | ✅ Implementado |

### 4. UI Routes (Partials HTML)

**Ubicación:** `apps/tenant/core/urls_ui.py` y apps específicas  
**Prefijo:** `/ui/{app}/` o `/workspace/`

| Ruta | Descripción | Estado |
|------|-------------|--------|
| `/workspace/` | Workspace principal (SPA) | ✅ Implementado |
| `/ui/landing/` | Partials de landing | ✅ Implementado |
| `/ui/dashboard/` | Partials de dashboard | ✅ Implementado |
| `/ui/empresa/` | Partials de empresa | ✅ Implementado |
| `/ui/perfil/` | Partials de perfil | ✅ Implementado |

### 5. Shells Estáticos (Redirects)

**Ubicación:** `config/urls_tenant.py`  
**Tipo:** Redirects a archivos estáticos

| Ruta | Destino | Estado |
|------|---------|--------|
| `/` | `/static/tenant/landing/index.html` o `/static/tenant/core/dashboard/index.html` | ✅ Implementado |
| `/login/` | `/static/tenant/landing/login.html` | ✅ Implementado |
| `/activate/` | `/static/tenant/landing/activate.html` | ✅ Implementado |
| `/dashboard/` | `/static/tenant/core/dashboard/index.html` | ✅ Implementado |
| `/empresa/` | `/static/tenant/core/empresa/index.html` | ✅ Implementado |
| `/facturas/` | `/static/tenant/core/facturas/index.html` | ✅ Implementado |
| `/contabilidad/` | `/static/tenant/core/contabilidad/index.html` | ✅ Implementado |

---

## 🔧 Plan de Implementación

### Fase 1: Implementar Core Auth Endpoints

**Objetivo:** Crear los endpoints de autenticación faltantes en Core API

#### 1.1 Crear ViewSet de Auth

**Archivo:** `apps/tenant/core/api/viewsets.py`

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from apps.public.tenants.models import TenantMembership

User = get_user_model()


class CoreAuthViewSet(viewsets.ViewSet):
    """
    ViewSet centralizado para autenticación en Core API.
    
    ⚠️ v2.61: Centraliza todos los endpoints de auth para tenants privados.
    """
    
    @action(detail=False, methods=['post'], url_path='login')
    def login(self, request):
        """
        POST /api/v1/core/auth/login/
        
        Autentica un usuario en el tenant actual.
        
        Body:
        {
            "email": "usuario@ejemplo.com",
            "password": "contraseña"
        }
        
        Response:
        {
            "success": true,
            "redirect_url": "/dashboard/",
            "user": {
                "id": 1,
                "email": "usuario@ejemplo.com",
                "first_name": "Nombre",
                "last_name": "Apellido"
            }
        }
        """
        email = request.data.get('email', '').lower().strip()
        password = request.data.get('password', '')
        
        if not email or not password:
            return Response(
                {"detail": "Email y contraseña son requeridos."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Autenticar usuario
        user = authenticate(request=request, username=email, password=password)
        
        if not user:
            return Response(
                {"detail": "Credenciales inválidas."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Verificar membresía en tenant actual
        try:
            membership = TenantMembership.objects.get(
                user=user,
                tenant=request.tenant,
                is_active=True
            )
        except TenantMembership.DoesNotExist:
            return Response(
                {"detail": "Usuario no tiene acceso a este tenant."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Realizar login de sesión
        login(request, user)
        
        # Construir redirect_url
        redirect_url = "/dashboard/"  # o desde settings
        
        return Response({
            "success": True,
            "redirect_url": redirect_url,
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
        })
    
    @action(detail=False, methods=['post'], url_path='logout')
    def logout(self, request):
        """
        POST /api/v1/core/auth/logout/
        
        Cierra la sesión del usuario actual.
        """
        logout(request)
        return Response({
            "success": True,
            "message": "Sesión cerrada correctamente."
        })
    
    # TODO: Implementar password-reset endpoints
    # @action(detail=False, methods=['post'], url_path='password-reset/request')
    # def password_reset_request(self, request):
    #     ...
```

#### 1.2 Registrar ViewSet en URLs

**Archivo:** `apps/tenant/core/api/urls.py`

```python
from apps.tenant.core.api.viewsets import CoreAuthViewSet

# Router base (/api/v1/core/)
router = DefaultRouter()
router.register(r"auth", CoreAuthViewSet, basename="core-auth")  # ✅ Agregar esta línea
```

#### 1.3 Actualizar Frontend (Opcional)

Si se quiere mantener compatibilidad con Landing API, el frontend puede usar Core API directamente:

```javascript
// Cambiar de:
const response = await fetch('/api/v1/core/auth/login/', { ... });

// A (si Core API está implementado):
const response = await fetch('/api/v1/core/auth/login/', { ... });
// O mantener Landing API como fallback:
const response = await fetch('/api/v1/landing/auth/login/', { ... });
```

### Fase 2: Migración Gradual

**Estrategia:** Mantener ambos endpoints durante un período de transición

1. **Implementar Core API endpoints** (Fase 1)
2. **Mantener Landing API endpoints** (compatibilidad)
3. **Actualizar frontend gradualmente** a Core API
4. **Deprecar Landing API endpoints** (después de migración completa)

### Fase 3: Documentación y Tests

1. **Actualizar documentación** en `documentacion/urls_mapping.md`
2. **Agregar tests** en `tests/tenant/core/test_core_auth_endpoints.py`
3. **Actualizar smoke tests** para verificar endpoints

---

## ✅ Checklist de Validación

### URLs Core API

- [x] `/api/v1/core/auth/login/` - POST ✅ **IMPLEMENTADO v2.61**
- [x] `/api/v1/core/auth/logout/` - POST ✅ **IMPLEMENTADO v2.61**
- [ ] `/api/v1/core/auth/password-reset/request/` - POST
- [ ] `/api/v1/core/auth/password-reset/validate/` - POST
- [ ] `/api/v1/core/auth/password-reset/confirm/` - POST
- [x] `/api/v1/core/landing/resumen/` - GET
- [x] `/api/v1/core/dashboard/sections/` - GET
- [x] `/api/v1/core/links/` - GET

### URLs Landing API (Alternativa)

- [x] `/api/v1/landing/info/` - GET
- [x] `/api/v1/landing/auth/login/` - POST
- [x] `/api/v1/landing/auth/activate/` - GET/POST

### URLs UI

- [x] `/workspace/` - Workspace principal
- [x] `/ui/landing/` - Partials landing
- [x] `/ui/dashboard/` - Partials dashboard
- [x] `/ui/empresa/` - Partials empresa
- [x] `/ui/perfil/` - Partials perfil

### Shells Estáticos

- [x] `/` - Redirect según autenticación
- [x] `/login/` - Shell estático login
- [x] `/activate/` - Shell estático activación
- [x] `/dashboard/` - Shell estático dashboard

---

## 📝 Notas de Implementación

### Consideraciones

1. **Compatibilidad:** Mantener Landing API como alternativa durante la migración
2. **Seguridad:** Validar TenantMembership en todos los endpoints de auth
3. **Sesiones:** Usar SessionAuthentication para mantener compatibilidad con frontend actual
4. **JWT:** Los endpoints JWT (`/api/token/`) siguen disponibles para aplicaciones móviles/SPA

### Referencias

- `documentacion/arquitectura_general.md` - Arquitectura general
- `documentacion/urls_mapping.md` - Mapeo de URLs
- `apps/tenant/landing/api/viewsets.py` - Implementación actual (Landing API)
- `apps/tenant/core/api/viewsets.py` - ViewSets de Core API

---

## 🎯 Próximos Pasos

1. ✅ **Implementar CoreAuthViewSet** en `apps/tenant/core/api/viewsets.py` - **COMPLETADO v2.61**
2. ✅ **Registrar ViewSet** en `apps/tenant/core/api/urls.py` - **COMPLETADO v2.61**
3. [ ] **Agregar tests** para verificar funcionalidad
4. [ ] **Actualizar frontend** para usar Core API (opcional, Landing API sigue funcionando)
5. [ ] **Documentar** cambios en `documentacion/urls_mapping.md`

---

## ✅ Implementación Completada (v2.61)

### Archivos Modificados

1. **`apps/tenant/core/api/viewsets.py`**
   - ✅ Agregado `CoreAuthViewSet` con acciones `login` y `logout`
   - ✅ Validación de credenciales y TenantMembership
   - ✅ Manejo de errores y logging

2. **`apps/tenant/core/api/urls.py`**
   - ✅ Registrado `CoreAuthViewSet` en el router
   - ✅ Endpoints disponibles: `/api/v1/core/auth/login/` y `/api/v1/core/auth/logout/`

### Características Implementadas

- ✅ Autenticación con email/username
- ✅ Validación de TenantMembership activa
- ✅ SessionAuthentication para compatibilidad con frontend
- ✅ Manejo de esquemas (public/tenant) con `connection.set_schema_to_public()`
- ✅ Logging completo para auditoría
- ✅ Respuestas JSON estructuradas
- ✅ Manejo de errores robusto

---

**Última actualización:** 2024-12-19  
**Versión del documento:** 1.1 (Implementación completada)
