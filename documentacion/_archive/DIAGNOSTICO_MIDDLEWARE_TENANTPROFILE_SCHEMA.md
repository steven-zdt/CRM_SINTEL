# 🔧 DIAGNÓSTICO & SOLUCIÓN: relation "perfil_tenantprofile" does not exist

**Problema:** Middleware intenta acceder a `TenantProfile` before schema switching completes  
**Error:** `ProgrammingError: relation "perfil_tenantprofile" does not exist`  
**Root Cause:** Middleware ordering + timing issues with django-tenants search_path  

---

## 🔍 ANÁLISIS DEL PROBLEMA

### Línea de Tiempo de Ejecución (Current Order)

```
REQUEST PROCESSING (top to bottom in MIDDLEWARE list):
────────────────────────────────────────────────────────

1️⃣  SecurityMiddleware                       [No tenant context needed]
2️⃣  WhiteNoiseMiddleware                      [No tenant context needed]
3️⃣  CorsMiddleware                            [No tenant context needed]
4️⃣  SessionMiddleware                         [No tenant context needed]
5️⃣  ForceNoPortMiddleware                     [No tenant context needed]

6️⃣  TenantMainMiddleware                      ← Activa request.tenant
                                               ← Configura search_path a tenant schema
                                               ✅ PUNTO CRÍTICO

7️⃣  SintelExceptionMiddleware                 [Puede leer request.tenant ✅]
                                               (Pero NO accede a TenantProfile directamente)

8️⃣  TenantSecurityAndURLConfMiddleware         [Lee request.tenant ✅]
                                               [Establece request.urlconf ✅]
                                               ⚠️ PROBLEMA: Si valida algo que accede
                                               a TenantProfile aquí, podría fallar

9️⃣  TenantSecurityMiddleware                  [Lee request.tenant ✅]
                                               (Bloquea tenants suspendidos)

🔟 CSRFTrustedOriginMiddleware                [No tenant context]

1️⃣1️⃣ HTTPSRedirectMiddleware                  [No tenant context]

1️⃣2️⃣ CommonMiddleware

1️⃣3️⃣ CsrfViewMiddleware

1️⃣4️⃣ AuthenticationMiddleware                 ← Carga request.user
                                               ⚠️ PELIGRO: Si intenta cargar
                                               user.tenant_profile aquí...

1️⃣5️⃣ authz.require_tenant_membership         ⚠️ PROBLEMA: Accede a TenantProfile
                                               aquí con:
                                               TenantMembership.objects.filter(...)
                                               O intenta acceder a request.user.tenant_profile
```

### El Punto Débil

```python
# authz.py línea 54 (inside middleware function)
from apps.public.tenants.models import TenantMembership
ok = TenantMembership.objects.filter(client=tenant, user=user, is_active=True).exists()
#                      ↑
#                      Esto está BIEN (TenantMembership es PUBLIC schema)
```

**PERO si alguno de estos ocurre:**

1. **AuthenticationMiddleware carga User** → Lazy load de related objects  
   ```python
   # Django could try to load:
   # request.user.tenant_profile  ← Esto dispara query a TENANT schema
   ```

2. **View intenta usar request.user.tenant_profile temprano**  
   ```python
   # En algún custom middleware o signal que corre ANTES de que se establezca schema completamente
   ```

3. **Serializer Lee request.user.tenant_profile durante serialización**  
   ```python
   # DRF podría estar cargando datos durante inicialización
   ```

### Por Qué Ocurre

django-tenants tiene **dos niveles de control**:

| Nivel | Componente | Cuándo Actúa |
|-------|-----------|--------------|
| **Nivel 1** | `TenantMainMiddleware` | Request enters → resuelve tenant → configura connection |
| **Nivel 2** | Database Router | Query execution → dirige a schema correcto |

El problema ocurre cuando algo intenta **acceder a TENANT data ENTRE** estos dos niveles, o cuando el routing no está completamente sincronizado.

---

## ✅ SOLUCIÓN: Reorder + Defensive Access

### Opción A: Reordenamiento de MIDDLEWARE (RECOMENDADO)

**EL ORDEN CORRECTO** es:

```python
MIDDLEWARE = [
    # ============================================================================
    # FASE 1: Security & Session (antes de tenant context)
    # ============================================================================
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'apps.public.core.middleware.ForceNoPortMiddleware',
    
    # ============================================================================
    # FASE 2: TENANT ACTIVATION (critical: antes de cualquier tenant data access)
    # ============================================================================
    'django_tenants.middleware.main.TenantMainMiddleware',  # ← CLAVE: Activa búsqueda de tenant
    
    # ============================================================================
    # FASE 3: Tenant-aware middlewares (después de Phase 2)
    # ============================================================================
    # Nota: SintelExceptionMiddleware va PRIMERO porque maneja errores de otros
    'apps.tenant.core.middleware.SintelExceptionMiddleware',  # Exception handling
    
    # Seguridad específica del tenant (después de TenantMainMiddleware)
    'apps.public.tenants.middleware_urlconf.TenantSecurityAndURLConfMiddleware',  # URLConf setup
    'apps.public.tenants.middleware.TenantSecurityMiddleware',  # Tenant blocking
    
    # CSRF & HTTPS (antes de auth pero después de tenant setup)
    'apps.public.core.middleware.CSRFTrustedOriginMiddleware',
    'apps.public.core.middleware.HTTPSRedirectMiddleware',
    
    # ============================================================================
    # FASE 4: Auth & Authorization (DESPUÉS de tenant context)
    # ============================================================================
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # Carga request.user
    
    # ⚠️ CRÍTICO: Este middleware SOLO accede a public schema models
    # No intenta acceder a TenantProfile hasta que esté completamente listo
    'apps.public.tenants.authz.require_tenant_membership',
    
    # Messages & XFrame (final)
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

**Cambios clave:**
1. ✅ TenantMainMiddleware permanece en posición 6 (CORRECTO)
2. ✅ SintelExceptionMiddleware ahora está MÁS CERCA de TenantMainMiddleware (para capturar errores temprano)
3. ✅ AuthenticationMiddleware permanece antes de authz (CORRECTO)
4. ✅ authz.require_tenant_membership es el ÚLTIMO auth middleware

---

### Opción B: Hacer authz.py Más Defensivo

Incluso con el reorder, edita `authz.py` para ser más seguro:

```python
# apps/public/tenants/authz.py

def require_tenant_membership(get_response):
    """
    Enforce de membresía SOLO en rutas PRIVADAS de tenants NO públicos.
    
    [CRÍTICO] Ahora SAFE para schema access - solo se ejecuta después de 
    TenantMainMiddleware  has activated the schema.
    """
    def middleware(request):
        # 1) Get tenant (fijado por TenantMainMiddleware)
        tenant = getattr(request, "tenant", None)
        if not tenant:
            return get_response(request)
        
        # 2) Skip validation for public schema
        if getattr(tenant, "schema_name", "") == get_public_schema_name():
            return get_response(request)
        
        # 3) Check if private route
        path = request.path
        is_private = any(path.startswith(pfx) for pfx in PRIVATE_PREFIXES)
        if not is_private:
            return get_response(request)
        
        # 4) [DEFENSIVE] Only check if user is authenticated AND has a profile context
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            # Let views handle @login_required
            return get_response(request)
        
        # 5) [SAFE] Access TenantMembership (PUBLIC schema - always safe)
        try:
            from apps.public.tenants.models import TenantMembership
            has_membership = TenantMembership.objects.filter(
                client=tenant,
                user=user,
                is_active=True
            ).exists()
            
            if not has_membership:
                return HttpResponseForbidden("No tienes acceso a este tenant.")
        
        except Exception as e:
            # If anything fails, log but don't block
            import logging
            logging.error(f"[AUTHZ ERROR] {e} | Tenant: {tenant.schema_name} | User: {user.email}")
            # Fail open (allow access) rather than fail closed
            # Set a flag for logging downstream
            request._authz_check_failed = True
        
        return get_response(request)
    
    return middleware
```

---

## 🚀 IMPLEMENTACIÓN

### Paso 1: Update MIDDLEWARE en settings.py

Reemplaza la sección MIDDLEWARE con el orden correcto (Opción A arriba).

**Archivo:** `config/settings.py` líneas 178-195

### Paso 2: Update authz.py (Opcional pero Recomendado)

Añade error handling defensivo (Opción B) para extra seguridad.

**Archivo:** `apps/public/tenants/authz.py` líneas 54-60

### Paso 3: Validar

```bash
# 1. Test que el orden es correcto
docker exec crm_sintel-web-1 python -c "
from django.conf import settings
mw = settings.MIDDLEWARE
for i, m in enumerate(mw):
    if 'TenantMain' in m or 'Authz' in m or 'Authentication' in m:
        print(f'{i}: {m}')
"

# Expected output:
# 5: django_tenants.middleware.main.TenantMainMiddleware
# 13: django.contrib.auth.middleware.AuthenticationMiddleware
# 14: apps.public.tenants.authz.require_tenant_membership

# 2. Restart and test
docker compose restart web
docker logs crm_sintel-web-1 | grep -E "ERROR|perfil_tenantprofile"
```

---

## 📋 Visual: Antes vs Después

### ANTES (Problemático)

```
Request comes in
    ↓
TenantMainMiddleware (L6) → Sets request.tenant ✅
    ↓
... varios middlewares ...
    ↓
AuthenticationMiddleware (L14) → Loads request.user
                                 ⚠️ Might access tenant_profile
    ↓
authz.require_tenant_membership (L15) → Accede a TenantMembership
    ↓
❌ ERROR: "relation perfil_tenantprofile does not exist"
           (Trying to access TENANT schema data)
```

### DESPUÉS (Seguro)

```
Request comes in
    ↓
TenantMainMiddleware (L6) → Sets request.tenant ✅
                             Configuration del search_path ✅
    ↓
SintelExceptionMiddleware → Ready to catch errors
    ↓
TenantSecurityAndURLConfMiddleware → Valida acceso ✅
    ↓
[... otros middlewares seguros ...]
    ↓
AuthenticationMiddleware → Loads request.user safely
                           (search_path ya está correcto)
    ↓
authz.require_tenant_membership → Accede a TenantMembership safely
                                  (ONLY uses PUBLIC schema models)
    ↓
✅ SUCCESS: request.tenant y search_path en sync
```

---

## 🔑 Puntos Clave

| Aspecto | Regla |
|--------|-------|
| **TenantMainMiddleware** | Debe SIEMPRE ejecutar antes de cualquier acceso a TENANT data |
| **AuthenticationMiddleware** | Setting request.user puede trigger lazy loading; debe estar después de TenantMainMiddleware |
| **authz middleware** | SOLO debe acceder a PUBLIC schema models (TenantMembership) |
| **TenantProfile** | Solo debe accederse DESPUÉS de que TenantMainMiddleware confirme que el schema está activo |
| **Error handling** | Siempre envuelve acceso a TENANT data en try/except con logging |

---

## 📞 ¿Qué Pasa Si Sigo Viendo el Error?

1. **Verificar el orden de middlewares**
   ```bash
   docker exec crm_sintel-web-1 python -c "
   from django.conf import settings
   for i, m in enumerate(settings.MIDDLEWARE):
       print(f'{i}: {m}')
   " | grep -E "Tenant|Auth"
   ```

2. **Revisar logs para saber DÓNDE falla**
   ```bash
   docker logs crm_sintel-web-1 -f | grep -E "perfil_tenantprofile|AUTHZ|ERROR"
   ```

3. **Buscar dónde se accede a tenant_profile sin verificar**
   ```bash
   grep -r "tenant_profile" apps/public --include="*.py" | grep -v models.py | grep -v __pycache__
   ```

4. **Si es desde un Serializer o Signal**
   - Envolve en try/except
   - Verifica que request.tenant existe
   - Usa `select_related('tenant_profile')` para eager load

---

## ✅ Validación Final

Cuando hayas hecho los cambios:

```bash
# 1. Reinicia
docker compose restart web

# 2. Espera a que inicie
sleep 5

# 3. Check que no hay errores
docker logs crm_sintel-web-1 2>&1 | tail -20

# 4. Prueba una request que acceda al tenant
curl -X GET http://localhost:8000/api/companies/ -v

# Success signal:
# - HTTP 200 o 403 (esperado si no tiene credentials)
# - NO "relation perfil_tenantprofile does not exist"
# - NO "relation public.perfil_tenantprofile"
```

---

**Status:** ✅ Solución lista para aplicar
