# 🔧 Eliminación de Referencias a /admin/login/ en Tenants Privados

## 📋 Objetivo

Eliminar todas las referencias a `/admin/login/` como vista principal de tenants privados, garantizando que:
- ✅ La **landing page** (`/`) sea la vista principal y por defecto
- ✅ El **login** (`/login/`) sea el punto de acceso de autenticación
- ✅ **NO** se use `/admin/login/` como vista principal

## 🔍 Auditoría Realizada

### Referencias Encontradas y Corregidas

1. **`config/settings.py`**
   - ❌ `LOGIN_URL = '/admin/login/'` → ✅ `LOGIN_URL = '/login/'`
   - ❌ `LOGOUT_REDIRECT_URL = '/admin/login/'` → ✅ `LOGOUT_REDIRECT_URL = '/'`

2. **`apps/tenant/core/views.py`**
   - ❌ `@method_decorator(login_required(login_url='/admin/login/'), ...)` 
   - ✅ `@method_decorator(login_required(login_url='/login/'), ...)`

3. **`apps/tenant/landing/api/viewsets.py`**
   - ❌ Ejemplo en documentación: `"login_url": "http://mi-empresa.com:8000/admin/login/"`
   - ✅ Actualizado: `"login_url": "http://mi-empresa.com:8000/login/"`

4. **`apps/tenant/landing/views.py`**
   - ⚠️ Comentario actualizado para reflejar que `/login/` es el login principal

### Referencias que Permanecen (No Críticas)

- **`apps/tenant/landing/views.py` (línea 150)**: Comentario en docstring mencionando `/admin/login/` como referencia histórica (no crítico)

## ✅ Cambios Implementados

### 1. Configuración Global (`config/settings.py`)

```python
# ANTES:
LOGIN_URL = '/admin/login/'
LOGOUT_REDIRECT_URL = '/admin/login/'

# DESPUÉS:
LOGIN_URL = '/login/'  # Login personalizado para tenants privados
LOGOUT_REDIRECT_URL = '/'  # Redirige a landing page después del logout
```

**Impacto:**
- `LoginRequiredMixin` ahora redirige a `/login/` en lugar de `/admin/login/`
- El logout redirige a la landing page (`/`) en lugar de `/admin/login/`

### 2. Decorador de Vista (`apps/tenant/core/views.py`)

```python
# ANTES:
@method_decorator(login_required(login_url='/admin/login/'), name='dispatch')

# DESPUÉS:
@method_decorator(login_required(login_url='/login/'), name='dispatch')
```

**Impacto:**
- Las vistas protegidas ahora redirigen a `/login/` cuando el usuario no está autenticado

### 3. Redirección de `/admin/login/` (`config/urls_tenant.py`)

Ya existía una redirección que envía `/admin/login/` a `/`:

```python
def tenant_admin_login_redirect(request):
    """Redirige /admin/login/ a la landing page (/) en tenants privados."""
    return redirect('/')
```

Esta redirección sigue activa y garantiza que cualquier intento de acceder a `/admin/login/` desde un tenant privado redirige a la landing page.

## 🎯 Flujo de Acceso Actualizado

### Para Usuarios Anónimos

1. **Acceso a `/`** → Muestra **Landing Page** (`TenantLandingView`)
2. **Click en "Iniciar Sesión"** → Redirige a `/login/` (`TenantLoginView`)
3. **Login exitoso** → Redirige a `/dashboard/` (`DashboardIndexView`)

### Para Usuarios Autenticados

1. **Acceso a `/`** → Redirige automáticamente a `/dashboard/`
2. **Acceso a `/login/`** → Redirige automáticamente a `/dashboard/` (ya está autenticado)
3. **Acceso a `/admin/login/`** → Redirige a `/` (landing page)

## 🔧 Herramientas de Auditoría

### Comando de Auditoría

```bash
# Auditar referencias a /admin/login/
docker compose exec web python manage.py auditar_referencias_admin_login

# El comando busca en:
# - apps/tenant/ (todo el código de tenants privados)
# - config/ (configuración de URLs)
```

### Resultado Esperado

```
✅ No se encontraron referencias a /admin/login/
```

Si se encuentran referencias, el comando las reporta con:
- 📄 Archivo y línea donde se encuentra
- 🔴 Tipo: código activo (crítico) o comentario (no crítico)
- 💡 Sugerencia de corrección

## 📊 Verificación

### 1. Verificar Configuración

```bash
docker compose exec web python manage.py shell
```

```python
from django.conf import settings
print(f"LOGIN_URL: {settings.LOGIN_URL}")
print(f"LOGOUT_REDIRECT_URL: {settings.LOGOUT_REDIRECT_URL}")
# Debe mostrar:
# LOGIN_URL: /login/
# LOGOUT_REDIRECT_URL: /
```

### 2. Verificar Redirecciones

```bash
# Probar acceso a /admin/login/ desde un tenant privado
curl -I http://home.sintel.net.co:8000/admin/login/
# Debe retornar: HTTP/1.1 302 Found (redirige a /)
```

### 3. Verificar Landing Page

```bash
# Probar acceso a / desde un tenant privado
curl -I http://home.sintel.net.co:8000/
# Debe retornar: HTTP/1.1 200 OK (muestra landing page)
```

## 🚨 Notas Importantes

### ⚠️ Esquema Público

El esquema público (`sintel.net.co` o `localhost`) **SÍ** usa `/admin/login/` porque:
- Es el admin de Django estándar
- Gestiona tenants, usuarios globales, catálogo DIAN, etc.
- No tiene landing page personalizada

### ✅ Tenants Privados

Los tenants privados (`home.sintel.net.co`, `cliente.sintel.net.co`, etc.) **NO** usan `/admin/login/` porque:
- Tienen landing page personalizada (`/`)
- Tienen login personalizado (`/login/`)
- El admin de tenant (`/admin/`) es aislado y solo muestra modelos de `TENANT_APPS`

## 📝 Resumen

| Aspecto | Antes | Después |
|---------|-------|---------|
| **Vista Principal** | `/admin/login/` | `/` (Landing Page) |
| **Login** | `/admin/login/` | `/login/` (TenantLoginView) |
| **Logout Redirect** | `/admin/login/` | `/` (Landing Page) |
| **LoginRequiredMixin** | Redirige a `/admin/login/` | Redirige a `/login/` |
| **Acceso a `/admin/login/`** | Muestra login del admin | Redirige a `/` |

## ✅ Estado Final

- ✅ Todas las referencias críticas a `/admin/login/` eliminadas
- ✅ Landing page (`/`) es la vista principal
- ✅ Login personalizado (`/login/`) funciona correctamente
- ✅ Redirección de `/admin/login/` a `/` activa
- ✅ Configuración global actualizada
- ✅ Auditoría automatizada disponible
