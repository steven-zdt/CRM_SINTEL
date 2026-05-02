# 🌐 Enrutamiento Diferenciado Público vs. Privado

**Versión:** 2.19  
**Fecha:** 2026-01-24  
**Estado:** ✅ IMPLEMENTADO Y VERIFICADO

---

## 🎯 Objetivo

El sistema detecta automáticamente si la petición entrante corresponde al dominio público (`sintel.com`) o a un tenant privado (`cliente.sintel.com`) y sirve interfaces completamente aisladas.

## 🏗️ Arquitectura

### Principio de Arquitectura

Utilizamos **TenantMainMiddleware** para la detección y **Dual URLConf** para el enrutamiento.

### Componentes Clave

1. **TenantMainMiddleware** (`django_tenants.middleware.main.TenantMainMiddleware`)
   - Detecta el tenant por dominio (HTTP_HOST)
   - Establece el esquema de base de datos activo
   - Inyecta `request.tenant` en la request

2. **Dual URLConf**
   - `ROOT_URLCONF = 'config.urls_public'` → Dominio público
   - `TENANT_URLCONF = 'config.urls_tenant'` → Tenants privados

3. **TenantLandingView** (Semáforo Inteligente)
   - Intercepta peticiones a la raíz (`/`) de tenants privados
   - Redirige usuarios autenticados al dashboard
   - Muestra landing page para usuarios anónimos

---

## ⚙️ Configuración

### TAREA 1: Configuración en `config/settings.py`

```python
# ⚠️ CONFIGURACIÓN CRÍTICA: URLs separadas para público y privado
# django-tenants usa ROOT_URLCONF para el esquema 'public' y TENANT_URLCONF para tenants
ROOT_URLCONF = 'config.urls_public'  # URLs para esquema público (sintel.com)
TENANT_URLCONF = 'config.urls_tenant'  # URLs para tenants privados (cliente.sintel.com)
```

**Estado:** ✅ Verificado y correcto

---

## 📋 Rutas Públicas (`config/urls_public.py`)

### TAREA 2: Definición de Rutas Públicas

**Archivo:** `config/urls_public.py`

**Contiene:**
- ✅ Admin global (`/admin/`)
- ✅ Consola de administración (`/console/`)
- ✅ APIs públicas (`/api/public/v1/`)
- ✅ APIs de administración (`/api/admin/v1/`)
- ✅ Home pública (`/` → `PublicIndexView`)

**NO contiene:**
- ❌ Rutas de dashboard privado
- ❌ Login de tenant
- ❌ APIs de tenant

**Estado:** ✅ Verificado y correcto

---

## 📋 Rutas Privadas (`config/urls_tenant.py`)

### TAREA 3: Definición de Rutas Privadas

**Archivo:** `config/urls_tenant.py`

**Estructura Requerida:**

```python
urlpatterns = [
    # 1. Landing Page (Ruta Raíz) - Semáforo Inteligente
    path('', include('apps.tenant.landing.urls')),  # ✅ TenantLandingView
    
    # 2. Dashboard Privado
    path('dashboard/', include('apps.tenant.dashboard.urls', namespace='tenant_dashboard')),
    
    # 3. Login Dedicado del Tenant
    path('login/', TenantLoginView.as_view(), name='login'),  # ✅ Login personalizado
    
    # 4. Admin Aislado del Tenant
    path('admin/login/', tenant_admin_login_redirect),  # Redirige a /
    path('admin/', tenant_admin_site.urls),  # Solo modelos de TENANT_APPS
    
    # 5. APIs del Tenant
    path('api/v1/', include('config.api_urls')),
]
```

**Estado:** ✅ Verificado y correcto

---

## 🚦 Controlador de Tráfico (`TenantLandingView`)

### TAREA 4: Implementación del Semáforo Inteligente

**Archivo:** `apps/tenant/landing/views.py`

**Clase:** `TenantLandingView`

**Lógica Estricta:**

```python
class TenantLandingView(TemplateView):
    template_name = 'tenant/landing/index.html'
    
    def dispatch(self, request, *args, **kwargs):
        """
        Traffic Controller: Redirige usuarios autenticados al dashboard.
        
        Caso A: Usuario autenticado → Redirige a /dashboard/
        Caso B: Usuario anónimo → Renderiza landing page
        """
        # Caso A: Usuario autenticado → Redirigir al dashboard
        if request.user.is_authenticated:
            try:
                dashboard_url = reverse('tenant_dashboard:index')
                return redirect(dashboard_url)
            except:
                return redirect('/dashboard/')
        
        # Caso B: Usuario anónimo → Renderizar landing page (NO REDIRIGIR)
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        """Inyecta tenant_name y login_url en el contexto."""
        context = super().get_context_data(**kwargs)
        context['tenant_name'] = getattr(self.request.tenant, 'nombre', 'Tenant')
        context['login_url'] = reverse('tenant_landing:login')  # /login/
        return context
```

**Estado:** ✅ Implementado y correcto

---

## 🧪 Tests de Verificación

### TAREA 5: Test de Verificación

**Archivo:** `tests/tenant/core/test_routing_logic.py`

**Tests Implementados:**

1. ✅ `test_public_domain_loads_public_urlconf`
   - Verifica que `sintel.com/` carga `urls_public`
   - Verifica que `PublicIndexView` se ejecuta

2. ✅ `test_private_tenant_anonymous_loads_landing_page`
   - Verifica que `cliente.sintel.com/` con usuario anónimo devuelve 200 OK
   - Verifica que se renderiza `tenant/landing/index.html`

3. ✅ `test_private_tenant_authenticated_redirects_to_dashboard`
   - Verifica que `cliente.sintel.com/` con usuario autenticado devuelve 302
   - Verifica que redirige a `/dashboard/`

4. ✅ `test_tenant_landing_view_dispatch_logic`
   - Verifica la lógica de "Semáforo Inteligente"
   - Caso A: Autenticado → Redirige
   - Caso B: Anónimo → Renderiza

5. ✅ `test_public_urlconf_excludes_tenant_routes`
   - Verifica que `/dashboard/` no existe en dominio público (404)

6. ✅ `test_tenant_urlconf_excludes_public_routes`
   - Verifica que `/console/` no existe en tenant privado (404)

7. ✅ `test_urlconf_separation_in_settings`
   - Verifica configuración de `ROOT_URLCONF` y `TENANT_URLCONF`

8. ✅ `test_tenant_landing_view_context`
   - Verifica que el contexto contiene `tenant_name` y `login_url`

**Estado:** ✅ Implementado

---

## 🔄 Flujo de Enrutamiento

### Escenario 1: Dominio Público (`sintel.com`)

```
1. Request HTTP → sintel.com/
2. TenantMainMiddleware detecta dominio público
3. Establece esquema 'public'
4. Django carga ROOT_URLCONF = 'config.urls_public'
5. Resuelve path('') → PublicIndexView
6. PublicIndexView redirige según estado del usuario:
   - Staff → /console/
   - Anónimo → /admin/login/
```

### Escenario 2: Tenant Privado Anónimo (`cliente.sintel.com`)

```
1. Request HTTP → cliente.sintel.com/
2. TenantMainMiddleware detecta tenant privado
3. Establece esquema 'cliente'
4. Django carga TENANT_URLCONF = 'config.urls_tenant'
5. Resuelve path('') → TenantLandingView
6. TenantLandingView.dispatch():
   - Usuario anónimo → Renderiza tenant/landing/index.html (200 OK)
   - NO redirige a login (acceso público permitido)
```

### Escenario 3: Tenant Privado Autenticado (`cliente.sintel.com`)

```
1. Request HTTP → cliente.sintel.com/ (usuario autenticado)
2. TenantMainMiddleware detecta tenant privado
3. Establece esquema 'cliente'
4. Django carga TENANT_URLCONF = 'config.urls_tenant'
5. Resuelve path('') → TenantLandingView
6. TenantLandingView.dispatch():
   - Usuario autenticado → Redirige a /dashboard/ (302 Redirect)
   - NO renderiza landing page
```

---

## ✅ Verificación de Implementación

### Checklist de Verificación

- [x] `config/settings.py` tiene `ROOT_URLCONF = 'config.urls_public'`
- [x] `config/settings.py` tiene `TENANT_URLCONF = 'config.urls_tenant'`
- [x] `config/urls_public.py` existe y contiene rutas públicas
- [x] `config/urls_tenant.py` existe y contiene rutas privadas
- [x] `config/urls_tenant.py` tiene `path('', include('apps.tenant.landing.urls'))`
- [x] `TenantLandingView` implementa `dispatch()` con lógica de redirección
- [x] `TenantLandingView` NO hereda de `LoginRequiredMixin`
- [x] Tests de verificación implementados y funcionando

---

## 🔒 Seguridad

### Aislamiento Garantizado

1. **URLConf Separado:**
   - Dominio público → `urls_public` (no tiene rutas de tenant)
   - Tenant privado → `urls_tenant` (no tiene rutas públicas)

2. **Middleware de Seguridad:**
   - `TenantSecurityMiddleware` bloquea rutas públicas en tenants privados
   - Retorna 404 si un tenant intenta acceder a `/console/` o `/api/public/v1/`

3. **Tests de Penetración:**
   - Tests automatizados verifican que no hay fugas de rutas
   - Verificación de 404 en rutas cruzadas

---

## 📚 Referencias

- **Documentación Principal:** `documentacion/arquitectura_general.md` (v2.19)
- **Middleware:** `apps/public/tenants/middleware.py`
- **Vista Landing:** `apps/tenant/landing/views.py`
- **Tests:** `tests/tenant/core/test_routing_logic.py`

---

## ✅ Estado Final

**Implementación:** ✅ COMPLETA  
**Verificación:** ✅ Tests implementados  
**Documentación:** ✅ Este documento

El sistema garantiza el enrutamiento diferenciado entre dominio público y tenants privados según la documentación oficial v2.19.
