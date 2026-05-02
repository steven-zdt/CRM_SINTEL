# Refactor API-First v2.30: Core como único gestor de UI (Tenants)

## ✅ Cambios Completados

### 1. Limpieza de Landing API (`apps/tenant/landing/api/urls.py`)

**Eliminados (movidos a Core API):**
- ❌ `/auth/login/` → `/api/v1/core/auth/login/`
- ❌ `/auth/logout/` → `/api/v1/core/auth/logout/`
- ❌ `/auth/password-reset/request/` → `/api/v1/core/auth/password-reset/request/`
- ❌ `/auth/password-reset/validate/` → `/api/v1/core/auth/password-reset/validate/`
- ❌ `/auth/password-reset/confirm/` → `/api/v1/core/auth/password-reset/confirm/`

**Mantenidos (específicos de Landing):**
- ✅ `/info/` → `LandingInfoView` (información pública del tenant)
- ✅ `/auth/activate/` → `OwnerActivationAPIView` (activación de owner)

### 2. Shells Estáticos Reubicados

**Nueva ubicación:** `apps/tenant/landing/static/tenant/landing/`

**Archivos creados:**
- ✅ `index.html` - Landing principal (consume `/api/v1/landing/info/`)
- ✅ `login.html` - Login (consume `/api/v1/core/auth/login/`)
- ✅ `reset-request.html` - Solicitar reset (consume `/api/v1/core/auth/password-reset/request/`)
- ✅ `reset-confirm.html` - Confirmar reset (consume `/api/v1/core/auth/password-reset/validate/` y `/confirm/`)
- ✅ `activate.html` - Activar cuenta (consume `/api/v1/landing/auth/activate/`)
- ✅ `js/landing.ui.js` - JS module para landing

**Eliminados:**
- ❌ `apps/tenant/core/static/tenant/core/landing/index.html`
- ❌ `apps/tenant/core/static/tenant/core/landing/reset/index.html`

### 3. Actualización de Referencias

**Archivos actualizados:**
- ✅ `config/urls_tenant.py` - Redirecciones actualizadas a `/static/tenant/landing/*.html`
- ✅ `apps/tenant/core/static/core/js/landing.ui.js` - Rutas actualizadas
- ✅ `apps/public/core/static/core/js/landing.ui.js` - Rutas actualizadas
- ✅ `apps/tenant/landing/services/password_reset.py` - URL de reset actualizada
- ✅ `apps/tenant/landing/api/views.py` - `login_api_url` actualizado a Core API
- ✅ `apps/tenant/landing/api/serializers.py` - Docstring actualizado
- ✅ `apps/services/onboarding/empresa_service.py` - Docstring actualizado

### 4. Navegación Secuencial

**Flujo completo:**
1. **Onboarding** → Link de activación
2. **Activación** → `/static/tenant/landing/activate.html` → POST `/api/v1/landing/auth/activate/`
3. **Login** → `/static/tenant/landing/login.html` → POST `/api/v1/core/auth/login/` → `redirect_url="/dashboard/"`
4. **Dashboard** → `/static/tenant/core/dashboard/index.html`
5. **Logout** → POST `/api/v1/core/auth/logout/` → `redirect_url="/"` → Landing

## 📍 Estructura Final

### URLs de API

**Core API (`/api/v1/core/`):**
- `/auth/login/` - Login centralizado
- `/auth/logout/` - Logout centralizado
- `/auth/password-reset/request/` - Solicitar reset
- `/auth/password-reset/validate/` - Validar token
- `/auth/password-reset/confirm/` - Confirmar reset

**Landing API (`/api/v1/landing/`):**
- `/info/` - Información pública del tenant
- `/auth/activate/` - Activación de owner

### Shells Estáticos

**Landing (`/static/tenant/landing/`):**
- `index.html` - Página principal (anónimos)
- `login.html` - Login
- `reset-request.html` - Solicitar reset
- `reset-confirm.html` - Confirmar reset
- `activate.html` - Activar cuenta

**Core (`/static/tenant/core/`):**
- `dashboard/index.html` - Dashboard (autenticados)
- `empresa/index.html` - Empresa
- `facturas/index.html` - Facturas
- `contabilidad/index.html` - Contabilidad
- `perfil/index.html` - Perfil

## 🔄 Redirecciones

**`TenantRootView` (`/`):**
- Usuario autenticado → `/static/tenant/core/dashboard/index.html`
- Usuario anónimo → `/static/tenant/landing/index.html`

**Short routes:**
- `/login/` → `/static/tenant/landing/login.html`
- `/activate/` → `/static/tenant/landing/activate.html`
- `/reset-password/` → `/static/tenant/landing/reset-request.html`
- `/reset-password/confirm/` → `/static/tenant/landing/reset-confirm.html`

## ✅ Criterios de Aceptación

- [x] Landing API solo expone `/info/` y `/auth/activate/`
- [x] Core API centraliza todos los endpoints de auth
- [x] Shells en `apps/tenant/landing/static/tenant/landing/`
- [x] No existen shells bajo `apps/tenant/core/static/tenant/core/landing/`
- [x] Todos los shells consumen Core API para auth
- [x] Navegación secuencial funcional
- [x] Referencias actualizadas en todo el código
- [x] `python manage.py check` sin errores

## 🧪 Próximos Pasos (Tests Smoke)

Pendiente crear tests smoke para:
- Login con Core API
- Logout con Core API
- Password reset flow completo
- Activación de cuenta
- Navegación secuencial
