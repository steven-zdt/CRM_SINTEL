# Arquitectura Core API v2.30 - Orquestador Único de UI Privada

**Versión:** 2.30  
**Fecha:** 2026-02-02  
**Estado:** ✅ Implementado y Verificado

---

## 🎯 Objetivo

Core API es el **orquestador único de la UI privada** y la **única fuente de verdad (SSoT) para autenticación** en el sistema. Todos los shells estáticos consumen exclusivamente Core API para interactuar con el backend.

---

## 📐 Principios Arquitectónicos

### 1. Core API = Orquestador Único
- **UI privada**: Todos los flujos de autenticación y presentación están en Core
- **SSoT de autenticación**: Login, logout, password-reset centralizados exclusivamente en `/api/v1/core/auth/*`
- **Landing vía Core**: Info y activate accesibles desde `/api/v1/core/landing/*`
- **Workspace**: Consume Core API para orquestación de datos de todas las TENANT_APPS

### 2. Landing API = Servicios de Dominio
- **Reducida a servicios**: `apps/tenant/landing/services/` contiene la lógica de dominio
- **API mínima**: Solo `info` y `activate` en `LandingViewSet` (compatibilidad interna)
- **Consumo vía Core**: La UI consume Core API, que internamente usa servicios de Landing

### 3. Separación de Responsabilidades
- **Landing Services**: Lógica de dominio (info, activate)
- **Core Services**: Orquestación y SSoT de auth
- **Core API**: Interfaz única para la UI
- **Shells Estáticos**: Consumen Core API exclusivamente

---

## 🏗️ Estructura de Servicios

### Core Services (`apps/tenant/core/services/`)

#### `auth_service.py` - SSoT de Autenticación
- `login_user()`: Autenticación y verificación de membresía
- `logout_user()`: Cierre de sesión con redirect_url
- `password_reset_request()`: Solicitud de reset (idempotente)
- `password_reset_validate()`: Validación de token
- `password_reset_confirm()`: Confirmación de reset con redirect_url
- `build_login_redirect()`: Construcción de URL de redirección al dashboard
- `build_post_confirm_redirect()`: Construcción de URL después de reset

#### `landing_adapter.py` - Adaptador de Landing
- `get_public_info_from_landing()`: Obtiene info pública del tenant
- `verify_activation_via_landing()`: Verifica token de activación
- `process_activation_via_landing()`: Procesa activación con contraseña

#### `orchestration.py` - Orquestación de Datos
- `get_dashboard_completo()`: Composición de dashboard desde múltiples apps
- `get_empresa_summary()`: Resumen de empresa (SSoT)
- `get_facturas_resumen()`: Resumen de facturas
- `get_contabilidad_resumen()`: Resumen de contabilidad
- `get_perfil_resumen()`: Resumen de perfil

### Landing Services (`apps/tenant/landing/services/`)

#### `landing_info_service.py` - Información Pública
- `get_public_info()`: Obtiene información pública del tenant con branding

#### `activation_service.py` - Activación de Owner
- `verify_activation_token()`: Verifica token y estado del usuario
- `process_activation()`: Procesa activación estableciendo contraseña

#### `password_reset.py` - Reset de Contraseña
- `request_reset()`: Solicita reset (usado por Core)
- `validate_token()`: Valida token (usado por Core)
- `confirm_reset()`: Confirma reset (usado por Core)

---

## 🔌 Endpoints Core API

### Autenticación (SSoT en Core)
```
POST /api/v1/core/auth/login/
POST /api/v1/core/auth/logout/
POST /api/v1/core/auth/password-reset/request/
POST /api/v1/core/auth/password-reset/validate/
POST /api/v1/core/auth/password-reset/confirm/
```

### Landing vía Core (UI Única)
```
GET  /api/v1/core/landing/info/
GET  /api/v1/core/landing/auth/activate/?token=...
POST /api/v1/core/landing/auth/activate/?token=...
```

### Orquestación de Datos
```
GET /api/v1/core/dashboard/
GET /api/v1/core/mi-empresa/
GET /api/v1/core/mi-perfil/
GET /api/v1/core/facturas/resumen/
GET /api/v1/core/contabilidad/resumen/
```

---

## 🎨 Shells Estáticos

### Ubicación
- `apps/tenant/landing/static/tenant/landing/*.html`

### Shells Principales
- `index.html`: Landing page (consume `/api/v1/core/landing/info/`)
- `login.html`: Login (consume `/api/v1/core/auth/login/`)
- `activate.html`: Activación (consume `/api/v1/core/landing/auth/activate/`)
- `reset-request.html`: Solicitud de reset (consume `/api/v1/core/auth/password-reset/request/`)
- `reset-confirm.html`: Confirmación de reset (consume `/api/v1/core/auth/password-reset/*`)

### Workspace
- `apps/tenant/core/templates/tenant/core/workspace.html`
- Consume Core API para orquestación de datos
- Carga partials lazy vía HTMX
- JavaScript consume `/api/v1/core/dashboard/` y otros endpoints Core

---

## 🔄 Flujo E2E Completo

### 1. Onboarding (Consola Pública)
- Crear tenant desde `/console/tenants/`
- Servicio: `apps.services.onboarding.empresa_service.crear_empresa()`
- Genera token de activación

### 2. Activación (Dominio del Tenant)
- Shell: `/static/tenant/landing/activate.html?token=...`
- API: `GET|POST /api/v1/core/landing/auth/activate/?token=...`
- Redirige a `/workspace/` después de activación

### 3. Login (UI Única)
- Shell: `/static/tenant/landing/login.html`
- API: `POST /api/v1/core/auth/login/`
- Redirige a `/workspace/` después de login

### 4. Workspace (Orquestación)
- Vista: `/workspace/`
- Template: `apps/tenant/core/templates/tenant/core/workspace.html`
- Consume: `/api/v1/core/dashboard/`, `/api/v1/core/mi-empresa/`, etc.

### 5. Logout
- API: `POST /api/v1/core/auth/logout/`
- Redirige a `/` (landing)

---

## ✅ Criterios de Aceptación

1. ✅ Toda funcionalidad de `apps/tenant/landing/services` accesible mediante `/api/v1/core/landing/*`
2. ✅ Autenticación disponible exclusivamente en `/api/v1/core/auth/*` con `redirect_url` para navegación
3. ✅ Shells estáticos consumen solo Core API
4. ✅ Workspace consume Core API para orquestación
5. ✅ Smoke tests E2E pasando para flujo completo
6. ✅ Sin duplicación de lógica entre Core y Landing
7. ✅ Sin hardcodes de marca (todo desde BD)

---

## 📚 Referencias

- Tests E2E: `tests/tenant/core/smoke/test_e2e_full_flow.py`
- Tests Workspace: `tests/tenant/core/smoke/test_e2e_workspace_verification.py`
- Documentación Flujo: `tests/tenant/core/smoke/FLUJO_E2E_SIMULADO.md`
- Arquitectura General: `documentacion/arquitectura_general.md`
