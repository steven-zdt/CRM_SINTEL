# ✅ Alineación Completa: Tenant Accesible por Dominio (django-tenants)

**Fecha:** 2026-01-29  
**Versión:** v2.22  
**Estado:** ✅ COMPLETO

---

## 📋 Criterios de Aceptación

### ✅ 1. Middlewares y URLConf (routing por dominio)

**Criterio:** `TenantMainMiddleware` muy arriba; el normalizador de host (si existe) va antes.

**Estado:** ✅ IMPLEMENTADO

**Verificación:**
- `ForceNoPortMiddleware` está **ANTES** de `TenantMainMiddleware` (línea 157-158 en `config/settings.py`)
- `TenantMainMiddleware` es el middleware crítico que resuelve el tenant por hostname
- Orden correcto: `SessionMiddleware` → `ForceNoPortMiddleware` → `TenantMainMiddleware`

**Configuración:**
```python
MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'apps.public.core.middleware.ForceNoPortMiddleware',  # Normaliza HTTP_HOST
    'django_tenants.middleware.main.TenantMainMiddleware',  # Resuelve tenant
    # ...
]
```

**URLConf:**
- ✅ `ROOT_URLCONF = 'config.urls_public'` (dominio público)
- ✅ `TENANT_URLCONF = 'config.urls_tenant'` (dominios de tenants)
- ✅ Rutas de tenant en `config/urls_tenant.py`: `/`, `/login/`, `/dashboard/`, `/api/v1/`

---

### ✅ 2. Client + Domain (sin puerto / sin "www") y esquema

**Criterio:** Client + Domain sin puerto/'www' creados en onboarding; `auto_create_schema=True` aplicado a nivel de clase.

**Estado:** ✅ IMPLEMENTADO

**Verificación:**

**Modelo Client:**
```python
# apps/public/tenants/models.py
class Client(TenantMixin):
    auto_create_schema = True  # ✅ A nivel de clase (no como argumento)
    # Al guardar, se crea/sincroniza el esquema del tenant automáticamente
```

**Modelo Domain:**
```python
# apps/public/tenants/models.py
class Domain(DomainMixin):
    domain = models.CharField(...)  # FQDN limpio (sin puerto, sin www)
    is_primary = models.BooleanField(...)  # Un primario por tenant
```

**Normalización:**
- ✅ Función `normalize_domain()` en `apps/public/tenants/utils.py`
- ✅ Elimina protocolo, www, rutas y **siempre puertos**
- ✅ Validador en `DomainSerializer.validate_domain()` rechaza dominios con puerto explícitamente

**Onboarding:**
- ✅ Servicio `crear_tenant_con_owner()` crea Client + Domain + TenantMembership
- ✅ Garantiza al menos un Domain principal por tenant (`is_primary=True`)

---

### ✅ 3. ROOT_URLCONF público y TENANT_URLCONF privado funcionando

**Criterio:** `/login/` de tenant responde bajo su dominio.

**Estado:** ✅ IMPLEMENTADO

**Verificación:**
- ✅ `ROOT_URLCONF = 'config.urls_public'` configurado
- ✅ `TENANT_URLCONF = 'config.urls_tenant'` configurado
- ✅ Rutas de tenant en `config/urls_tenant.py`:
  - `/` → `TenantLandingView` (landing page)
  - `/login/` → `TenantLoginView` (login HTML)
  - `/dashboard/` → Dashboard del tenant
  - `/api/v1/` → APIs REST del tenant

**Flujo:**
1. Usuario accede a `http://miempresa.localhost/login/`
2. `ForceNoPortMiddleware` normaliza `HTTP_HOST` → `miempresa.localhost`
3. `TenantMainMiddleware` busca `Domain` en esquema `public` y fija el esquema del tenant
4. Django usa `TENANT_URLCONF = 'config.urls_tenant'`
5. Ruta `/login/` se resuelve a `TenantLoginView`

---

### ✅ 4. Usuario propietario y TenantMembership creados

**Criterio:** Login exitoso en el dominio del tenant; acceso a apps `apps/tenant/*`.

**Estado:** ✅ IMPLEMENTADO

**Verificación:**

**Servicio de Onboarding:**
```python
# apps/services/onboarding/empresa_service.py
@transaction.atomic
def crear_tenant_con_owner(
    nombre: str,
    owner_email: Optional[str] = None,
    owner_password: Optional[str] = None,
    admin_user_id: Optional[int] = None,
    # ...
) -> Tuple[Client, Domain, str]:
    # 1) Usuario global (public)
    if owner_email:
        admin_user, created = User.objects.get_or_create(email=owner_email, ...)
        if created:
            admin_user.set_password(owner_password)
            admin_user.save()
    # 2) Client (auto_create_schema=True)
    client, _ = Client.objects.get_or_create(schema_name=..., ...)
    # 3) Domain (sin puerto)
    domain, _ = Domain.objects.get_or_create(domain=normalize_domain(...), ...)
    # 4) TenantMembership
    TenantMembership.objects.update_or_create(
        client=client, user=admin_user,
        defaults={"rol": "ADMIN", "is_primary_admin": True, "is_active": True}
    )
    # 5) Seed opcional (schema_context)
    with schema_context(client.schema_name):
        obtener_o_crear_perfil(user=admin_user, ...)
    # 6) Login URL
    return client, domain, login_url
```

**Autenticación:**
- ✅ `TenantAwareBackend` valida membresía contra el tenant antes de permitir acceso
- ✅ El middleware ya activó el esquema correcto por hostname
- ✅ Usuario puede logear en `/login/` del `TENANT_URLCONF`

---

### ✅ 5. (Prod) ALLOWED_HOSTS con dominios/subdominios correctos

**Criterio:** (Dev) subdominios `.localhost` resueltos.

**Estado:** ✅ IMPLEMENTADO

**Configuración:**
```python
# config/settings.py
ALLOWED_HOSTS = [
    f".{TENANT_DOMAIN_BASE}",  # .sintel.com o .localhost
    TENANT_DOMAIN_BASE,  # sintel.com o localhost
    "localhost",
    ".localhost",  # ✅ Subdominios locales (dev)
    "127.0.0.1",
]
```

**Verificación:**
- ✅ Desarrollo: `.localhost` permite subdominios (`miempresa.localhost`)
- ✅ Producción: Lista explícita de dominios/subdominios (no `'*'`)
- ✅ `DEBUG=True`: Django valida `.localhost` y `127.0.0.1` automáticamente

---

### ✅ 6. Tests de routing/membresía/dominio sin puerto en verde

**Criterio:** Tests de garantía pasando.

**Estado:** ✅ IMPLEMENTADO

**Ubicación:** `tests/public/tenants/test_tenant_domain_access.py`

**Tests implementados:**
1. ✅ `test_routing_por_hostname_activa_tenant_urlconf` - Routing por hostname activa `TENANT_URLCONF`
2. ✅ `test_domain_sin_puerto_es_obligatorio` - Dominios con puerto son rechazados
3. ✅ `test_normalize_domain_removes_port` - `normalize_domain()` elimina puertos siempre
4. ✅ `test_membresia_obligatoria_para_acceso` - Usuario sin membresía no puede acceder
5. ✅ `test_unique_primary_domain_per_tenant` - Solo un dominio primario por tenant
6. ✅ `test_domain_global_uniqueness` - Un dominio no puede pertenecer a múltiples tenants
7. ✅ `test_tenant_accessible_only_by_its_domain` - Aislamiento por dominio

**Ejecución:**
```bash
docker compose exec web pytest tests/public/tenants/test_tenant_domain_access.py -v
```

---

## 📝 Resumen de Cambios Implementados

### 1. Normalización de Dominios
- ✅ `normalize_domain()` elimina puertos siempre (conforme a doc oficial)
- ✅ `DomainSerializer.validate_domain()` rechaza explícitamente dominios con puerto
- ✅ Documentación actualizada

### 2. Servicio de Onboarding
- ✅ Función `crear_tenant_con_owner()` acepta `owner_email`/`owner_password` para crear usuario
- ✅ Usa `schema_context()` para seed opcional (utilidad oficial)
- ✅ Retorna `login_url` sin puerto

### 3. Middleware Stack
- ✅ `ForceNoPortMiddleware` antes de `TenantMainMiddleware`
- ✅ Orden correcto: `SessionMiddleware` → `ForceNoPortMiddleware` → `TenantMainMiddleware`

### 4. URLConf
- ✅ `ROOT_URLCONF = 'config.urls_public'` (dominio público)
- ✅ `TENANT_URLCONF = 'config.urls_tenant'` (dominios de tenants)
- ✅ Rutas de tenant: `/`, `/login/`, `/dashboard/`, `/api/v1/`

### 5. Tests de Garantía
- ✅ 7 tests implementados cubriendo todos los casos críticos
- ✅ Tests validan routing, normalización, membresía y aislamiento

### 6. Documentación
- ✅ Sección "Acceso por Dominio" añadida a `arquitectura_general.md`
- ✅ Este documento de alineación creado

---

## 🎯 Conformidad con Documentación Oficial

**Referencias:**
- [django-tenants Documentation](https://django-tenants.readthedocs.io/)
- [Django URL Configuration](https://docs.djangoproject.com/en/stable/topics/http/urls/)

**Conformidad:** ✅ 100%

- ✅ Routing por hostname (no subcarpeta)
- ✅ Dominios sin puerto (FQDN puro)
- ✅ `auto_create_schema=True` a nivel de clase
- ✅ `schema_context()` para seed opcional
- ✅ `TENANT_URLCONF` activo en dominios de tenants
- ✅ Usuario global + membresía por tenant
- ✅ `ALLOWED_HOSTS` configurado correctamente

---

## ✅ Estado Final

**Todos los criterios de aceptación están cumplidos.**

El proyecto está completamente alineado con la documentación oficial de django-tenants para acceso por dominio. Cada tenant privado es accesible exclusivamente por su dominio (hostname), el middleware resuelve el tenant por host y cambia el `search_path` al esquema del tenant, las rutas del tenant se sirven vía `TENANT_URLCONF` y el usuario propietario puede logear en `/login/` bajo ese dominio.

---

**Última Actualización:** 2026-01-29  
**Mantenido por:** Equipo de Desarrollo SINTEL
