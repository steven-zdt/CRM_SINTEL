# Alineación Final Landing API v2.30

## ✅ Estado Actual Verificado

### 1. Landing API Unificada

**✅ Completado:**
- `apps/tenant/landing/api/viewsets.py` - ViewSet unificado con acciones:
  - `info` → GET `/api/v1/landing/info/`
  - `activate` → GET|POST `/api/v1/landing/auth/activate/`
- `apps/tenant/landing/api/urls.py` - Router con DefaultRouter
- `apps/tenant/landing/api/views.py` - ❌ ELIMINADO

### 2. Endpoints de Auth

**✅ Core API (`/api/v1/core/auth/*`):**
- `/login/` ✅
- `/logout/` ✅
- `/password-reset/request/` ✅
- `/password-reset/validate/` ✅
- `/password-reset/confirm/` ✅

**✅ Landing API (`/api/v1/landing/`):**
- `/info/` ✅
- `/auth/activate/` ✅

**❌ No existen endpoints duplicados en Landing API**

### 3. Shells Estáticos

**✅ Ubicación correcta:**
- `apps/tenant/landing/static/tenant/landing/index.html` ✅
- `apps/tenant/landing/static/tenant/landing/login.html` ✅
- `apps/tenant/landing/static/tenant/landing/reset-request.html` ✅
- `apps/tenant/landing/static/tenant/landing/reset-confirm.html` ✅
- `apps/tenant/landing/static/tenant/landing/activate.html` ✅
- `apps/tenant/landing/static/tenant/landing/js/landing.ui.js` ✅

**✅ Consumo de APIs:**
- `login.html` → `/api/v1/core/auth/login/` ✅
- `reset-request.html` → `/api/v1/core/auth/password-reset/request/` ✅
- `reset-confirm.html` → `/api/v1/core/auth/password-reset/validate/` y `/confirm/` ✅
- `activate.html` → `/api/v1/landing/auth/activate/` ✅
- `index.html` → `/api/v1/landing/info/` ✅

**✅ Enlaces internos:**
- Botón "Iniciar Sesión" → `/static/tenant/landing/login.html` ✅
- No hay referencias a `/static/tenant/core/landing/*` ✅

### 4. Limpieza

**✅ Eliminado:**
- `apps/tenant/landing/api/views.py` ✅
- `apps/tenant/core/static/tenant/core/landing/` ✅

**⚠️ Templates Partial (Workspace Compositor):**
- `apps/tenant/landing/templates/tenant/landing/partials/*.html` - Se mantienen porque:
  - Son HTML estructural sin datos (API-First)
  - Se usan en el workspace compositor (`/workspace/`)
  - No renderizan datos del backend, solo estructura
  - El JS carga datos desde APIs JSON

### 5. Montajes de Rutas

**✅ Verificado:**
- `config/urls_tenant.py`: `path('api/v1/landing/', include('apps.tenant.landing.api.urls', namespace='tenant_landing_api'))` ✅
- `config/api_urls.py`: `path('core/', include('apps.tenant.core.api.urls'))` ✅
- `/api/v1/core/*` expuesto correctamente ✅

## ✅ Criterios de Aceptación

- [x] **A)** Solo existe `viewsets.py` (sin `views.py`); Landing API expone únicamente `/info/` y `/auth/activate/` mediante router
- [x] **B)** `/api/v1/core/auth/*` es la única fuente para login, logout y password-reset/*
- [x] **C)** Todos los shells están bajo `/static/tenant/landing/*.html`; no existen referencias a `/static/tenant/core/landing/*`; shells consumen Core para auth y Landing para activate
- [x] **D)** Navegación coherente: creación de cliente → activación (Landing) → login (Core) → dashboard → logout (Core)

## 📍 Flujo de Usuario

1. **Onboarding** → Link de activación
2. **Activación** → `GET /api/v1/landing/auth/activate/?token=...` → `POST /api/v1/landing/auth/activate/?token=...` → `redirect_url="/dashboard/"`
3. **Login** → `POST /api/v1/core/auth/login/` → `redirect_url="/dashboard/"`
4. **Dashboard** → `/static/tenant/core/dashboard/index.html`
5. **Logout** → `POST /api/v1/core/auth/logout/` → `redirect_url="/"` → Landing

## 🔍 Notas

- Los templates partials en `apps/tenant/landing/templates/` se mantienen porque son HTML estructural para el workspace compositor, no templates dinámicos con datos del backend.
- Todos los shells consumen Core API para auth y Landing API para activate.
- No hay HTML dinámico renderizado por el backend (API-First).
