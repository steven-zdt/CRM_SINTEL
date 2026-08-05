# ADR-002: Registro Dual de Endpoints en Schemas Publico y Tenant

**Estado:** ACCEPTED  
**Fecha:** 2026-06-09  
**Autores:** Sintel Engineering  
**Relacionado con:** ADR-001 (Pull Model), feat/onboarding-cookie

---

## Contexto

`home.sintel.net.co` es el dominio de la consola de administracion y del flujo de onboarding.  
En django-tenants, este dominio resuelve al **schema publico** y usa `config/urls_public.py` como ROOT_URLCONF.

Los subdominios de empresa (`acme.sintel.net.co`, `empresa.sintel.net.co`, etc.) resuelven al **schema del tenant** y usan `config/urls_tenant.py` (via TENANT_URLCONF).

Esto crea una trampa frecuente: un endpoint creado en `CoreAuthViewSet` (registrado en `urls_tenant.py`) **no existe** cuando se lo llama desde `home.sintel.net.co`. El resultado es un HTTP 404 silencioso.

### Incidente que origino este ADR

El flujo de activacion de cuenta (`activate.html`) es un archivo estatico servido desde ambos dominios. Cuando el usuario llega desde el email de bienvenida con tenant `home`, la URL de activacion es `https://home.sintel.net.co/static/tenant/core/auth/activate.html`. Las llamadas API de esa pagina:

- `POST /api/v1/core/auth/resend-activation-code/` → **404** (solo en `urls_tenant.py`)
- `POST /api/v1/core/auth/activate-with-code/`     → **404** (solo en `urls_tenant.py`)

Ademas, aunque el endpoint existiera, la validacion `payload.tenant_id != request.tenant.id` falla en schema publico porque `request.tenant` es el Client del schema publico, no el Client del tenant `home`.

---

## Decision

### Regla 1 — Paginas estaticas: registrar en ambos URL confs

Cualquier endpoint llamado desde una pagina estatica (`/static/...`) que sea accesible desde `home.sintel.net.co` **debe estar registrado en ambos URL confs**:

| URL conf | Ruta | Para que dominio |
|---|---|---|
| `config/urls_tenant.py` (via `api_urls.py`) | `/api/v1/core/auth/<action>/` | `acme.sintel.net.co` |
| `config/public_api_urls.py` | `/api/public/v1/auth/<action>/` | `home.sintel.net.co` |

El mismo ViewSet action puede servir ambas rutas si detecta el schema internamente.

### Regla 2 — Deteccion de schema en el handler

Cuando un endpoint debe funcionar en ambos schemas, usar el patron:

```python
request_tenant = getattr(request, "tenant", None)
is_public_schema = (
    request_tenant is None
    or getattr(request_tenant, "schema_name", None) == "public"
)
```

**En schema publico:** `request.tenant` es el Client del schema `public`. Para operar sobre el tenant correcto, resolverlo desde:
- El payload de Redis: `Client.objects.get(id=payload["tenant_id"])`
- La membresia del usuario: `TenantMembership.objects.filter(user=user).select_related("client").first()`

**Nunca** comparar `payload.tenant_id == request.tenant.id` sin antes verificar que no estamos en el schema publico.

### Regla 3 — Frontend: URL adaptativa

Las paginas estaticas que pueden ser servidas desde ambos dominios deben detectar el hostname para construir la URL correcta:

```javascript
const IS_PUBLIC_DOMAIN = (function () {
    const host = window.location.hostname;
    return (
        host === 'home.sintel.net.co' ||
        host === 'sintel.net.co' ||
        host === 'localhost' ||
        /^\d+\.\d+\.\d+\.\d+$/.test(host)
    );
})();

function getApiUrl(action) {
    if (IS_PUBLIC_DOMAIN) {
        return '/api/public/v1/auth/' + action + '/';
    }
    return '/api/v1/core/auth/' + action + '/';
}
```

---

## Registro en `config/public_api_urls.py`

El patron de registro dual usa `try/except` para no bloquear el arranque si el ViewSet falla al importar:

```python
# config/public_api_urls.py
try:
    from apps.tenant.core.api.viewsets import CoreAuthViewSet as _CoreAuthViewSet
    urlpatterns += [
        path(
            'auth/activate-with-code/',
            _CoreAuthViewSet.as_view({'post': 'activate_with_code'}),
            name='public-activate-with-code',
        ),
        path(
            'auth/resend-activation-code/',
            _CoreAuthViewSet.as_view({'post': 'resend_activation_code'}),
            name='public-resend-activation-code',
        ),
    ]
except Exception:
    pass
```

---

## Checklist para nuevos endpoints en paginas de onboarding/activacion

Antes de dar por finalizado cualquier endpoint llamado desde `activate.html`, `login.html` u otras paginas estaticas:

- [ ] El endpoint esta en `CoreAuthViewSet` (u otro ViewSet de tenant)
- [ ] Esta registrado en `config/api_urls.py` o `config/urls_tenant.py`
- [ ] **Esta registrado en `config/public_api_urls.py`** bajo `auth/<action>/`
- [ ] El handler detecta `is_public_schema` y resuelve el tenant correctamente
- [ ] El frontend usa `getApiUrl(action)` en vez de URL hardcoded
- [ ] Prueba manual desde `home.sintel.net.co` (no solo desde subdominio de tenant)

---

## Consecuencias

**Positivas:**
- Los flujos de onboarding funcionan desde cualquier dominio de entrada
- Un solo handler cubre ambos casos (no duplicacion de logica)
- El checklist previene recurrencia

**Negativas:**
- Los endpoints de activacion quedan expuestos en el schema publico (aceptable: son de uso unico, con Redis TTL, y no exponen datos sensibles)
- `public_api_urls.py` importa desde `apps.tenant.*` (cruce de capa) — mitigado con `try/except` para evitar bloqueos en arranque

---

## Archivos modificados en el incidente

| Archivo | Cambio |
|---|---|
| `apps/tenant/core/api/viewsets.py` | `activate_with_code` y `resend_activation_code`: deteccion de schema publico + resolucion de tenant desde payload/membresia |
| `config/public_api_urls.py` | Registro de `activate-with-code` y `resend-activation-code` bajo `/api/public/v1/auth/` |
| `apps/tenant/core/static/tenant/core/auth/activate.html` | `IS_PUBLIC_DOMAIN` + `getApiUrl(action)` en lugar de URLs hardcoded |
