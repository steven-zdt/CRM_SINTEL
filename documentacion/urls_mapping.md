# Mapeo de URLs: Landing API vs Core API

## 📍 Registro de URLs

### 1. Landing API (`apps/tenant/landing/api/urls.py`)
**Registrado en:** `config/urls_tenant.py` línea 150
```python
path('api/v1/landing/', include('apps.tenant.landing.api.urls', namespace='tenant_landing_api')),
```

**URLs disponibles:**
- `GET /api/v1/landing/info/` → `LandingInfoView` (información pública del tenant)
- `POST /api/v1/landing/auth/login/` → `TenantLoginAPIView`
- `POST /api/v1/landing/auth/logout/` → `TenantLogoutAPIView`
- `GET/POST /api/v1/landing/auth/activate/` → `OwnerActivationAPIView`
- `POST /api/v1/landing/auth/password-reset/request/` → `PasswordResetRequestAPIView` ⚠️ DEPRECADO
- `POST /api/v1/landing/auth/password-reset/validate/` → `PasswordResetValidateAPIView` ⚠️ DEPRECADO
- `POST /api/v1/landing/auth/password-reset/confirm/` → `PasswordResetConfirmAPIView` ⚠️ DEPRECADO

### 2. Core API (`apps/tenant/core/api/urls.py`)
**Registrado en:** `config/api_urls.py` línea 42
```python
path('core/', include('apps.tenant.core.api.urls')),
```

**URLs disponibles:**
- `GET /api/v1/core/landing/resumen/` → `LandingResumenView` (resumen de landing)
- `POST /api/v1/core/auth/login/` → `CoreAuthViewSet.login` ✅ **IMPLEMENTADO v2.61**
- `POST /api/v1/core/auth/logout/` → `CoreAuthViewSet.logout` ✅ **IMPLEMENTADO v2.61**
- `POST /api/v1/core/auth/password-reset/request/` → `PasswordResetRequestView` ⚠️ **PENDIENTE**
- `POST /api/v1/core/auth/password-reset/validate/` → `PasswordResetValidateView` ⚠️ **PENDIENTE**
- `POST /api/v1/core/auth/password-reset/confirm/` → `PasswordResetConfirmView` ⚠️ **PENDIENTE**

## 🔄 Relación entre Landing y Core

### Endpoints Duplicados (Core es la versión centralizada)

| Endpoint | Landing API | Core API | Estado |
|----------|-------------|----------|--------|
| Login | `/api/v1/landing/auth/login/` | `/api/v1/core/auth/login/` | ✅ **Core implementado v2.61** |
| Logout | `/api/v1/landing/auth/logout/` | `/api/v1/core/auth/logout/` | ✅ **Core implementado v2.61** |
| Password Reset Request | `/api/v1/landing/auth/password-reset/request/` | `/api/v1/core/auth/password-reset/request/` | ⚠️ **Pendiente en Core** |
| Password Reset Validate | `/api/v1/landing/auth/password-reset/validate/` | `/api/v1/core/auth/password-reset/validate/` | ⚠️ **Pendiente en Core** |
| Password Reset Confirm | `/api/v1/landing/auth/password-reset/confirm/` | `/api/v1/core/auth/password-reset/confirm/` | ⚠️ **Pendiente en Core** |

### Endpoints Únicos

| Endpoint | Ubicación | Descripción |
|----------|-----------|-------------|
| `/api/v1/landing/info/` | Landing API | Información pública del tenant (mantener) |
| `/api/v1/landing/auth/activate/` | Landing API | Activación de owner (mantener) |
| `/api/v1/core/landing/resumen/` | Core API | Resumen de landing para composición |

## ⚠️ Política de Migración

1. **Core API es la fuente de verdad** para auth (login, logout, password-reset)
2. **Landing API** mantiene endpoints específicos (info, activate)
3. **Los endpoints de Landing están marcados como DEPRECADOS** pero se mantienen por compatibilidad
4. **Nuevos desarrollos deben usar Core API** (`/api/v1/core/auth/*`)

## ✅ Estado de Implementación (v2.61)

### Implementado
- ✅ `POST /api/v1/core/auth/login/` - `CoreAuthViewSet.login` (v2.61)
- ✅ `POST /api/v1/core/auth/logout/` - `CoreAuthViewSet.logout` (v2.61)

### Características
- Validación de credenciales (email/username)
- Validación de TenantMembership activa
- SessionAuthentication para compatibilidad con frontend
- Manejo de esquemas (public/tenant)
- Logging completo para auditoría
- Respuestas JSON estructuradas

### Pendiente
- ⚠️ Endpoints de password-reset (request/validate/confirm)

## 📂 Estructura de Archivos

```
config/
├── urls_tenant.py          # Registra: /api/v1/landing/
└── api_urls.py            # Registra: /api/v1/core/

apps/tenant/
├── landing/
│   └── api/
│       └── urls.py        # URLs de landing (parcialmente deprecadas)
└── core/
    └── api/
        └── urls.py        # URLs de Core (centralizadas) ✅
```
