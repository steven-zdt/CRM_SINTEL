# Enrutamiento Definitivo para Tenants Privados

## ✅ Configuración Implementada

### Estructura de URLs (`config/urls_tenant.py`)

**Este archivo solo se carga en dominios privados (tenants).**

```python
urlpatterns = [
    # 1. Landing Page (Ruta Raíz) - Maneja la lógica de redirección
    path('', include('apps.tenant.landing.urls')),
    
    # 2. Dashboard Privado (Interfaz Principal)
    path('dashboard/', include('apps.tenant.dashboard.urls', namespace='tenant_dashboard')),
    
    # 3. Admin de Django (Versión Tenant)
    path('admin/', admin.site.urls),
    
    # 4. APIs del Tenant (Aisladas)
    path('api/v1/', include('config.api_urls')),
]
```

---

## 🔄 Flujo de Enrutamiento

### Caso 1: Usuario Anónimo accede a `cliente.sintel.net.co/`

1. **Request:** `GET /` desde `cliente.sintel.net.co`
2. **URLConf:** `config/urls_tenant.py` (TENANT_URLCONF)
3. **Ruta:** `path('', include('apps.tenant.landing.urls'))`
4. **Vista:** `TenantLandingView`
5. **Lógica:**
   - Verifica `request.user.is_authenticated` → `False`
   - **Resultado:** Renderiza `tenant/landing/index.html` (Landing Page)

**✅ Resultado:** Usuario anónimo ve la Landing Page del tenant.

---

### Caso 2: Usuario Logueado accede a `cliente.sintel.net.co/`

1. **Request:** `GET /` desde `cliente.sintel.net.co`
2. **URLConf:** `config/urls_tenant.py` (TENANT_URLCONF)
3. **Ruta:** `path('', include('apps.tenant.landing.urls'))`
4. **Vista:** `TenantLandingView`
5. **Lógica:**
   - Verifica `request.user.is_authenticated` → `True`
   - Redirige a `reverse('tenant_dashboard:index')` → `/dashboard/`
   - **Resultado:** Redirección automática a `/dashboard/`

**✅ Resultado:** Usuario logueado es redirigido automáticamente al Dashboard.

---

### Caso 3: Usuario accede a `cliente.sintel.net.co/dashboard/`

1. **Request:** `GET /dashboard/` desde `cliente.sintel.net.co`
2. **URLConf:** `config/urls_tenant.py` (TENANT_URLCONF)
3. **Ruta:** `path('dashboard/', include('apps.tenant.dashboard.urls', namespace='tenant_dashboard'))`
4. **Vista:** `DashboardIndexView`
5. **Lógica:**
   - `LoginRequiredMixin` verifica autenticación
   - Verifica membresía del usuario en el tenant
   - Determina el rol del usuario (ADMIN, STAFF, USER)
   - **Si es ADMIN:** Renderiza `tenant/dashboard/admin_index.html`
   - **Si es USER/STAFF:** Renderiza `tenant/dashboard/user_index.html`

**✅ Resultado:** Usuario ve el Dashboard con datos del tenant según su rol.

---

## 📋 Archivos Clave

### 1. `config/urls_tenant.py`
- **Función:** Configuración principal de URLs para tenants privados
- **Namespace:** `tenant_dashboard` para el dashboard
- **Aislamiento:** NO incluye rutas públicas (`/console/`, `/api/public/v1/`)

### 2. `apps/tenant/landing/urls.py`
- **Función:** URLs de la landing page
- **Namespace:** `tenant_landing`
- **Rutas:**
  - `''` → `TenantLandingView` (raíz)
  - `'login/'` → `TenantLoginView` (login personalizado)

### 3. `apps/tenant/dashboard/urls.py`
- **Función:** URLs del dashboard
- **Namespace:** `tenant_dashboard`
- **Rutas:**
  - `''` → `DashboardIndexView` (dashboard principal)

### 4. `apps/tenant/landing/views.py`
- **Vista:** `TenantLandingView`
- **Lógica:** Traffic Controller
  - Si autenticado → Redirige a `/dashboard/`
  - Si anónimo → Renderiza landing page

### 5. `apps/tenant/dashboard/views.py`
- **Vista:** `DashboardIndexView`
- **Lógica:** Control de roles
  - Verifica autenticación (`LoginRequiredMixin`)
  - Verifica membresía en tenant
  - Selecciona template según rol:
    - `admin_index.html` para ADMIN
    - `user_index.html` para USER/STAFF

---

## 🔒 Garantías de Seguridad

### 1. Aislamiento por URLConf
- ✅ `config/urls_tenant.py` NO contiene rutas públicas
- ✅ Las rutas públicas (`/console/`, `/api/public/v1/`) no existen en tenants
- ✅ Resultado: `404 Not Found` automático

### 2. Control de Acceso
- ✅ `DashboardIndexView` requiere autenticación (`LoginRequiredMixin`)
- ✅ Verifica membresía del usuario en el tenant
- ✅ Bloquea acceso si el usuario no tiene membresía (`PermissionDenied`)

### 3. Redirección Inteligente
- ✅ Usuarios autenticados son redirigidos automáticamente al dashboard
- ✅ Usuarios anónimos pueden ver la landing page sin autenticación
- ✅ No hay redirecciones infinitas

---

## 🧪 Verificación

### Test Manual

1. **Usuario Anónimo:**
   ```bash
   # Acceder a http://cliente.sintel.net.co:8000/
   # Resultado esperado: Landing Page visible
   ```

2. **Usuario Logueado:**
   ```bash
   # Acceder a http://cliente.sintel.net.co:8000/
   # Resultado esperado: Redirección automática a /dashboard/
   ```

3. **Dashboard:**
   ```bash
   # Acceder a http://cliente.sintel.net.co:8000/dashboard/
   # Resultado esperado: Dashboard visible (requiere autenticación)
   ```

### Tests Automatizados

```bash
# Ejecutar tests de routing
docker compose exec web python manage.py test tests.tenant.landing.test_routing_guarantee

# Ejecutar tests de dashboard
docker compose exec web python manage.py test tests.tenant.dashboard.test_access
```

---

## 📚 Referencias

- `config/urls_tenant.py` - Configuración principal de URLs
- `apps/tenant/landing/views.py` - Vista de landing page (Traffic Controller)
- `apps/tenant/dashboard/views.py` - Vista de dashboard (Control de roles)
- `apps/tenant/dashboard/templates/tenant/dashboard/admin_index.html` - Template del dashboard para ADMIN
- `documentacion/VALIDACION_AISLAMIENTO_ESTRICTO.md` - Validación de aislamiento

---

## ✅ Estado Final

**Implementación:** ✅ **COMPLETA**

- ✅ Enrutamiento configurado correctamente
- ✅ Redirección inteligente implementada
- ✅ Dashboard con control de roles funcionando
- ✅ Aislamiento de rutas garantizado
- ✅ Tests de validación disponibles

El sistema está listo para producción con enrutamiento definitivo para tenants privados.
