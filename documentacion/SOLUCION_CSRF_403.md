# Solución: Error 403 CSRF en Login Admin (home.com)

## Problema

Al intentar hacer login en `/admin/login/` desde `http://home.com/admin/login/`, se recibe:

```
403 (Forbidden)
Verificación CSRF fallida. Solicitud abortada.
```

## Diagnóstico

### 1. Verificar que el middleware está activo

El middleware `CSRFTrustedOriginMiddleware` debe estar en `MIDDLEWARE` **ANTES** de `CsrfViewMiddleware`:

```python
MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',
    'apps.public.tenants.middleware.TenantSecurityMiddleware',
    'apps.public.core.middleware.CSRFTrustedOriginMiddleware',  # ✅ Debe estar aquí
    # ... otros middlewares ...
    'django.middleware.csrf.CsrfViewMiddleware',  # ✅ Validación CSRF aquí
]
```

### 2. Verificar configuración de CSRF en desarrollo

En `config/settings.py`, cuando `DEBUG=True`:

```python
# CSRF Cookie Domain (debe ser None en desarrollo)
CSRF_COOKIE_DOMAIN = None  # ✅ Permite cualquier dominio
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = False  # ✅ No requiere HTTPS
CSRF_COOKIE_HTTPONLY = False
```

### 3. Verificar que el dominio está en CSRF_TRUSTED_ORIGINS

El middleware `CSRFTrustedOriginMiddleware` agrega automáticamente el dominio a `CSRF_TRUSTED_ORIGINS` en desarrollo.

**Para verificar manualmente**, agrega temporalmente en `config/settings.py`:

```python
if DEBUG:
    CSRF_TRUSTED_ORIGINS.extend([
        "http://home.com",  # ✅ Agregar manualmente si es necesario
        "http://localhost",
        "http://127.0.0.1",
    ])
```

## Soluciones

### Solución 1: Verificar que DEBUG=True

Asegúrate de que `DEBUG=True` en tu `.env`:

```bash
DJANGO_DEBUG=True
```

### Solución 2: Limpiar cookies del navegador

1. Abre DevTools (F12)
2. Ve a **Application** → **Cookies** → `http://home.com`
3. Elimina todas las cookies (especialmente `csrftoken`)
4. Recarga la página

### Solución 3: Verificar que el token CSRF se genera

1. Abre DevTools (F12) → **Network**
2. Recarga la página de login
3. Busca el request a `/admin/login/`
4. En **Response Headers**, verifica que hay una cookie `csrftoken`
5. En el HTML del formulario, busca `<input type="hidden" name="csrfmiddlewaretoken" value="...">`

### Solución 4: Agregar dominio manualmente (temporal)

Si el middleware no funciona, agrega el dominio manualmente en `config/settings.py`:

```python
# 3. CSRF Trusted Origins
CSRF_TRUSTED_ORIGINS = [
    f"https://*.{TENANT_DOMAIN_BASE}",
    f"http://*.{TENANT_DOMAIN_BASE}",
]

if DEBUG:
    CSRF_TRUSTED_ORIGINS.extend([
        "http://localhost",
        "http://127.0.0.1",
        f"http://{TENANT_DOMAIN_BASE}",
        f"http://*.{TENANT_DOMAIN_BASE}",
        "http://home.com",  # ✅ Agregar manualmente
    ])
```

### Solución 5: Verificar que el tenant existe

Asegúrate de que existe un `Domain` con `domain='home.com'` en la base de datos:

```python
# En Django shell
from apps.public.tenants.models import Domain, Client

# Verificar que existe el dominio
domain = Domain.objects.filter(domain='home.com').first()
print(domain)  # Debe mostrar el dominio

# Si no existe, crear el tenant y dominio
client = Client.objects.create(schema_name='home', name='Home')
Domain.objects.create(domain='home.com', tenant=client, is_primary=True)
```

## Advertencia sobre Cross-Origin-Opener-Policy

El warning sobre `Cross-Origin-Opener-Policy` es **solo informativo** y no bloquea la funcionalidad. Es normal en desarrollo con HTTP (no HTTPS).

Para suprimirlo completamente, puedes:

1. **Usar localhost en lugar de dominios arbitrarios**:
   ```
   http://localhost:8000/admin/login/
   ```

2. **O configurar HTTPS local** (más complejo, requiere certificados)

## Verificación Final

Después de aplicar las soluciones:

1. **Recarga la página de login** (Ctrl+F5 para forzar recarga)
2. **Verifica que el token CSRF está presente** en el formulario
3. **Intenta hacer login** nuevamente

Si el problema persiste:

1. **Revisa los logs de Django** para ver el error exacto
2. **Verifica que el middleware está en el orden correcto**
3. **Confirma que `DEBUG=True`**

## Referencias

- [Django CSRF Protection](https://docs.djangoproject.com/en/5.0/ref/csrf/)
- [CSRF_TRUSTED_ORIGINS](https://docs.djangoproject.com/en/5.0/ref/settings/#csrf-trusted-origins)
- [Middleware CSRF](https://docs.djangoproject.com/en/5.0/ref/middleware/#django.middleware.csrf.CsrfViewMiddleware)
