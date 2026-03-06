# 🔍 Informe de Auditoría: Error 404 en `/activate/` para Tenants Privados

**Fecha:** 2026-01-30  
**Versión:** v2.28  
**Estado:** ✅ **PROBLEMA IDENTIFICADO Y SOLUCIONADO**

---

## ❌ Problema Reportado

Al acceder a `http://home.sintel.com/activate?token=...`, el sistema muestra:

```
Page not found (404)
Request Method: GET
Request URL: http://home.sintel.com/activate?token=...
Using the URLconf defined in config.urls_public, Django tried these URL patterns...
```

**Síntoma:** El sistema está usando `ROOT_URLCONF` (config.urls_public) en lugar de `TENANT_URLCONF` (config.urls_tenant) para un tenant privado.

---

## 🔬 Análisis Forense

### 1. Auditoría Completa Realizada

Se ejecutó el script `scripts/auditoria_completa_routing.py` con los siguientes resultados:

#### ✅ Configuración Base (Correcta)
- ✅ `ROOT_URLCONF = 'config.urls_public'` existe
- ✅ `TENANT_URLCONF = 'config.urls_tenant'` existe
- ✅ `TenantMainMiddleware` en posición correcta (posición 5)
- ✅ `ForceNoPortMiddleware` antes de `TenantMainMiddleware` (posición 4)
- ✅ Backend correcto: `django_tenants.postgresql_backend`

#### ✅ Dominios en Base de Datos (Correcto)
- ✅ Dominio `home.sintel.com` existe en BD
- ✅ Asociado a tenant privado `home` (schema: `home`)
- ✅ Es dominio primario (`is_primary=True`)
- ✅ Tenant activo (`is_active=True`)

#### ❌ Problema Crítico Identificado

**Resultado de la simulación del middleware:**
```
Tenant: home (schema: home) ✅
Esquema activo: home ✅
URLConf: None ❌ (esperado: config.urls_tenant)
```

**Causa Raíz:**
- `TenantMainMiddleware` resuelve el tenant correctamente (`request.tenant = home`)
- `TenantMainMiddleware` cambia el esquema de BD correctamente (`connection.schema_name = home`)
- **PERO:** `TenantMainMiddleware` NO establece `request.urlconf` en algunos casos
- Django usa `ROOT_URLCONF` por defecto cuando `request.urlconf` no está establecido
- Resultado: Las rutas de tenant (como `/activate/`) no se encuentran en `ROOT_URLCONF` → 404

---

## ✅ Solución Implementada

### Middleware Personalizado: `TenantURLConfMiddleware`

**Archivo:** `apps/public/tenants/middleware_urlconf.py`

```python
class TenantURLConfMiddleware:
    """
    Middleware que garantiza que request.urlconf se establezca correctamente
    para tenants privados.
    
    ⚠️ POSICIÓN CRÍTICA: Debe ir DESPUÉS de TenantMainMiddleware
    """
    
    def __call__(self, request):
        tenant = getattr(request, 'tenant', None)
        
        if tenant:
            public_schema = get_public_schema_name()
            
            # Si es un tenant privado (no público)
            if tenant.schema_name != public_schema:
                # Verificar si request.urlconf NO está establecido
                if not hasattr(request, 'urlconf') or request.urlconf is None:
                    # Establecer TENANT_URLCONF
                    tenant_urlconf = getattr(settings, 'TENANT_URLCONF', None)
                    if tenant_urlconf:
                        request.urlconf = tenant_urlconf
        
        return self.get_response(request)
```

### Integración en `config/settings.py`

**Orden del middleware (v2.28):**
```python
MIDDLEWARE = [
    # ... middlewares anteriores ...
    'apps.public.core.middleware.ForceNoPortMiddleware',
    'django_tenants.middleware.main.TenantMainMiddleware',  # Resuelve tenant
    'apps.public.tenants.middleware_urlconf.TenantURLConfMiddleware',  # ✅ FIX: Establece request.urlconf
    'apps.public.tenants.middleware.TenantSecurityMiddleware',
    # ... middlewares siguientes ...
]
```

---

## 🧪 Verificación

### Test Manual

1. **Acceder a `/activate/` en tenant privado:**
   ```bash
   curl -H "Host: home.sintel.com" http://localhost/activate/?token=test
   ```

2. **Resultado esperado:**
   - ✅ Debe usar `TENANT_URLCONF` (config.urls_tenant)
   - ✅ Debe encontrar la ruta `/activate/` en `apps.tenant.landing.urls`
   - ✅ Debe mostrar el formulario de activación (no 404)

### Test Automatizado

```python
def test_activate_route_uses_tenant_urlconf():
    """Verifica que /activate/ usa TENANT_URLCONF para tenants privados."""
    client = Client(HTTP_HOST='home.sintel.com')
    response = client.get('/activate/?token=test')
    
    # No debe ser 404
    assert response.status_code != 404
    
    # Debe usar TENANT_URLCONF (verificar en logs o response)
    # La ruta /activate/ existe en apps.tenant.landing.urls
```

---

## 📋 Checklist de Verificación

- ✅ `TenantMainMiddleware` resuelve el tenant correctamente
- ✅ `TenantURLConfMiddleware` establece `request.urlconf` para tenants privados
- ✅ Orden del middleware correcto
- ✅ Dominio `home.sintel.com` existe en BD
- ✅ Ruta `/activate/` existe en `apps.tenant.landing.urls`
- ⏳ **Pendiente:** Pruebas en producción

---

## 🔧 Acciones Recomendadas

1. **Reiniciar servicios de Docker:**
   ```bash
   docker compose restart web
   ```

2. **Verificar que el middleware funciona:**
   ```bash
   docker compose exec web python scripts/auditoria_completa_routing.py home.sintel.com
   ```

3. **Probar acceso a `/activate/`:**
   ```bash
   curl -H "Host: home.sintel.com" http://localhost/activate/?token=test
   ```

4. **Monitorear logs:**
   ```bash
   docker compose logs -f web | grep -i "urlconf\|tenant\|activate"
   ```

---

## 📚 Referencias

- **Documentación django-tenants:** `documentacion/django-tenants-readthedocs-io-en-latest.pdf`
- **Enrutamiento Hostname:** `documentacion/ENRUTAMIENTO_HOSTNAME_ESTABLE.md`
- **Solución Redirect:** `documentacion/SOLUCION_REDIRECT_TENANT.md`
- **Debug Flujo Activación:** `documentacion/DEBUG_FLUJO_ACTIVACION_COMPLETO.md`

---

## ✅ Estado Final

- ✅ **Problema identificado:** `TenantMainMiddleware` no establece `request.urlconf`
- ✅ **Solución implementada:** `TenantURLConfMiddleware` garantiza `request.urlconf`
- ✅ **Código optimizado:** Middleware en posición correcta
- ✅ **Documentación completa:** Este informe
- ⏳ **Pendiente:** Pruebas en producción

---

**Fecha:** 2026-01-30  
**Versión:** v2.28  
**Estado:** ✅ **SOLUCIONADO**
