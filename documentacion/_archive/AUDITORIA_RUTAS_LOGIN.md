# 🔍 Auditoría de Rutas de Login - SINTEL

**Fecha:** 2026-01-24  
**Objetivo:** Documentar todas las rutas de login y verificar hacia qué endpoints apuntan (público vs privado)

---

## 📋 Resumen Ejecutivo

El proyecto SINTEL tiene **rutas de login separadas** según el contexto:
- **Esquema Público** (`public`): Login del admin de Django
- **Tenants Privados** (`tenant_*`): Login específico del tenant

---

## 🏛️ ESQUEMA PÚBLICO (public)

### Ruta: `/login/`

**Ubicación:** `config/urls.py` (línea 99)

```python
path('login/', lambda request: redirect('admin:login'), name='login'),
```

**Endpoint Final:** `/admin/login/` (Admin de Django público)

**Comportamiento:**
- Redirige automáticamente al login del admin de Django
- Usado para acceder a la consola de administración pública
- Disponible solo cuando se accede al esquema `public`

**Vista:** `django.contrib.admin.sites.AdminSite.login` (por defecto)

**Acceso:**
- URL: `http://localhost:8000/login/` → redirige a `/admin/login/`
- URL: `http://sintel.net.co/login/` → redirige a `/admin/login/` (en producción)

---

## 🏢 TENANTS PRIVADOS (tenant_*)

### Ruta: `/login/` (HTML)

**Ubicación:** `apps/tenant/landing/urls.py` (línea 19)

```python
path('login/', views.TenantLoginView.as_view(), name='login'),
```

**Endpoint:** `TenantLoginView` (vista HTML)

**Vista:** `apps/tenant.landing.views.TenantLoginView`

**Comportamiento:**
- Renderiza template `tenant/landing/login.html`
- Usa `TenantAuthenticationForm` para validar credenciales y membresía del tenant
- Redirige a `/dashboard/` después de login exitoso
- Si el usuario ya está autenticado, redirige automáticamente al dashboard

**Acceso:**
- URL: `http://cliente.localhost:8000/login/` (desarrollo)
- URL: `https://cliente.sintel.net.co/login/` (producción)

**Características:**
- ✅ Validación de `TenantMembership` (el usuario debe pertenecer al tenant)
- ✅ Verificación de `is_active` en la membresía
- ✅ Redirección automática si ya está autenticado

---

### Ruta: `/api/v1/landing/auth/login/` (API REST)

**Ubicación:** `apps/tenant/landing/api/urls.py` (línea 15)

```python
path("auth/login/", TenantLoginAPIView.as_view(), name="login"),
```

**Endpoint:** `TenantLoginAPIView` (API REST - DRF)

**Vista:** `apps.tenant.landing.api.views.TenantLoginAPIView`

**Comportamiento:**
- Endpoint REST para autenticación programática
- Usa `TenantLoginSerializer` para validación
- Retorna JWT tokens o realiza login de sesión según configuración
- Permite integración con frontend SPA o aplicaciones móviles

**Acceso:**
- URL: `http://cliente.localhost:8000/api/v1/landing/auth/login/` (desarrollo)
- URL: `https://cliente.sintel.net.co/api/v1/landing/auth/login/` (producción)

**Método:** `POST`

**Body:**
```json
{
  "username": "usuario@ejemplo.com",
  "password": "contraseña"
}
```

**Características:**
- ✅ Arquitectura API-First
- ✅ Validación de `TenantMembership`
- ✅ Compatible con JWT y Session Auth

---

## 🔄 Flujo de Resolución de Rutas

### Esquema Público (`public`)

```
http://localhost:8000/login/
  ↓
config/urls.py (ROOT_URLCONF)
  ↓
redirect('admin:login')
  ↓
/admin/login/ (Admin de Django público)
```

### Tenant Privado (`tenant_*`)

```
http://cliente.localhost:8000/login/
  ↓
django-tenants detecta el dominio y carga TENANT_URLCONF
  ↓
config/urls_tenant.py (TENANT_URLCONF)
  ↓
include('apps.tenant.landing.urls')
  ↓
apps/tenant/landing/urls.py
  ↓
TenantLoginView.as_view() (HTML)
```

---

## ⚠️ Puntos Críticos

### 1. Conflicto de Nombres

**Problema:** Ambas rutas usan `name='login'` pero en diferentes namespaces:
- Público: `name='login'` (sin namespace)
- Privado: `name='login'` en `app_name='tenant_landing'`

**Solución:** ✅ No hay conflicto porque:
- Público usa `ROOT_URLCONF` (`config/urls.py`)
- Privado usa `TENANT_URLCONF` (`config/urls_tenant.py`)
- Django resuelve correctamente según el esquema activo

### 2. Redirección de `/admin/login/` en Tenants

**Ubicación:** `config/urls_tenant.py` (línea 67)

```python
path('admin/login/', tenant_admin_login_redirect, name='admin-login-redirect'),
```

**Comportamiento:**
- Cualquier intento de acceder a `/admin/login/` en un tenant privado
- Redirige automáticamente a `/` (landing page)
- **Motivo:** Ocultar el admin de Django en tenants privados por seguridad

**Función:**
```python
def tenant_admin_login_redirect(request):
    """Redirige /admin/login/ a la raíz (/) en tenants privados."""
    return redirect('/')
```

### 3. Configuración de `LOGIN_URL`

**Ubicación:** `config/settings.py`

```python
LOGIN_URL = '/login/'
```

**Comportamiento:**
- `LoginRequiredMixin` y decoradores `@login_required` usan esta URL
- En público: redirige a `/login/` → `/admin/login/`
- En privado: redirige a `/login/` → `TenantLoginView`

**✅ Correcto:** La configuración es relativa y se resuelve según el contexto.

---

## 📊 Tabla Comparativa

| Contexto | Ruta | Endpoint | Vista | Propósito |
|----------|------|----------|-------|-----------|
| **Público** | `/login/` | `/admin/login/` | Admin Django | Acceso a consola pública |
| **Privado** | `/login/` | `TenantLoginView` | HTML Template | Login del tenant |
| **Privado** | `/api/v1/landing/auth/login/` | `TenantLoginAPIView` | API REST | Login programático |

---

## ✅ Verificación de Endpoints

### Endpoint Público

```bash
# Verificar que /login/ redirige a /admin/login/ en público
curl -I http://localhost:8000/login/
# Debe retornar: 302 Found → Location: /admin/login/
```

### Endpoint Privado (HTML)

```bash
# Verificar que /login/ carga TenantLoginView en tenant privado
curl -I http://cliente.localhost:8000/login/
# Debe retornar: 200 OK (template HTML)
```

### Endpoint Privado (API)

```bash
# Verificar que la API de login funciona
curl -X POST http://cliente.localhost:8000/api/v1/landing/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}'
# Debe retornar: 200 OK (con tokens) o 400 Bad Request (credenciales inválidas)
```

---

## 🎯 Conclusión

**Estado:** ✅ **CORRECTO**

Todas las rutas de login están correctamente configuradas:
- ✅ Separación clara entre público y privado
- ✅ No hay conflictos de nombres
- ✅ Redirecciones funcionan correctamente
- ✅ Arquitectura API-First implementada

**Recomendación:** Mantener la estructura actual. La separación de rutas según el esquema es correcta y sigue las mejores prácticas de django-tenants.
