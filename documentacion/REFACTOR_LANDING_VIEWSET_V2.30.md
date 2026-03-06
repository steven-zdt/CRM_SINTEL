# Refactor Landing API: Unificación en ViewSet (v2.30)

## ✅ Cambios Completados

### 1. Unificación de Views → ViewSet

**Eliminado:**
- ❌ `apps/tenant/landing/api/views.py` (757 líneas)

**Consolidado en:**
- ✅ `apps/tenant/landing/api/viewsets.py` - ViewSet unificado con acciones:
  - `info` → GET `/api/v1/landing/info/`
  - `activate` → GET|POST `/api/v1/landing/auth/activate/`

### 2. Router con DefaultRouter

**Antes:**
```python
urlpatterns = [
    path('info/', LandingInfoView.as_view(), name='info'),
    path('auth/activate/', OwnerActivationAPIView.as_view(), name='activate'),
]
```

**Después:**
```python
router = DefaultRouter()
router.register(r'', LandingViewSet, basename='landing')
urlpatterns = [path('', include(router.urls))]
```

### 3. Endpoints Expuestos

**Landing API (`/api/v1/landing/`):**
- ✅ `GET /info/` → `LandingViewSet.info`
- ✅ `GET|POST /auth/activate/` → `LandingViewSet.activate`

**Core API (`/api/v1/core/`):**
- ✅ `/auth/login/`
- ✅ `/auth/logout/`
- ✅ `/auth/password-reset/*`

### 4. Verificación de Montajes

**`config/urls_tenant.py`:**
```python
path('api/v1/landing/', include('apps.tenant.landing.api.urls', namespace='tenant_landing_api'))
```

**`config/api_urls.py`:**
```python
path('core/', include('apps.tenant.core.api.urls'))
```

### 5. Limpieza

**Archivos eliminados:**
- ❌ `apps/tenant/landing/api/views.py`

**Archivos mantenidos (legítimos):**
- ✅ `apps/tenant/landing/templates/tenant/landing/partials/*.html` - Partials para UI compositor
- ✅ `apps/tenant/landing/urls_ui.py` - URLs para partials UI
- ✅ `apps/tenant/landing/views_ui.py` - Views para partials UI

**Referencias verificadas:**
- ✅ No hay imports de `views.py` en el código
- ✅ No hay referencias a `/static/tenant/core/landing/*`
- ✅ Todos los shells en `/static/tenant/landing/*.html`

## 📍 Estructura Final

```
apps/tenant/landing/api/
├── __init__.py
├── serializers.py
├── urls.py          # Router con DefaultRouter
└── viewsets.py      # ViewSet unificado (info + activate)
```

## ✅ Criterios de Aceptación

- [x] Solo existe `viewsets.py` (sin `views.py`)
- [x] ViewSet expone exclusivamente `/info/` y `/auth/activate/` mediante router
- [x] No existen endpoints de login/logout/password-reset en Landing
- [x] Todos los shells en `/static/tenant/landing/*.html`
- [x] No hay referencias rotas
- [x] `python manage.py check` sin errores
- [x] `collectstatic --dry-run` sin errores

## 🔄 Flujo de Usuario

1. **Onboarding** → Link de activación
2. **Activación** → `GET /api/v1/landing/auth/activate/?token=...` → `POST /api/v1/landing/auth/activate/?token=...`
3. **Login** → `POST /api/v1/core/auth/login/` → `redirect_url="/dashboard/"`
4. **Dashboard** → `/static/tenant/core/dashboard/index.html`
5. **Logout** → `POST /api/v1/core/auth/logout/` → `redirect_url="/"`
