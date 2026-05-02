# 📋 Changelog: Versiones 2.27 y 2.28

**Fecha:** 2026-01-30  
**Versión:** v2.27 → v2.28

---

## 🔧 v2.27 - Solución Error Redirect después de Activación

### Problema Identificado

Después de la activación de un tenant privado mediante `http://cliente.sintel.com/activate?token=...`, el sistema redirigía al usuario al URLConf público (`ROOT_URLCONF`) en lugar de mantenerlo en el URLConf del tenant (`TENANT_URLCONF`).

### Causa Raíz

El uso de `reverse('tenant_dashboard:index')` después de `login()` podía ejecutarse en un contexto donde el URLConf no estaba correctamente preservado, causando que Django usara el `ROOT_URLCONF` por defecto.

### Solución Implementada

**Archivo:** `apps/tenant/landing/views.py`

- Cambio de `redirect(reverse('tenant_dashboard:index'))` a URL absoluta
- Uso de `redirect(f"{protocol}://{domain.domain}/dashboard/")` para garantizar que el middleware resuelva el tenant correctamente
- Consulta del dominio primario del tenant usando `schema_context('public')`

### Archivos Modificados

1. `apps/tenant/landing/views.py` - `ActivateOwnerView.form_valid()`
2. `documentacion/SOLUCION_REDIRECT_TENANT.md` (nuevo)
3. `documentacion/INFORME_ERROR_REDIRECT_TENANT.md` (nuevo)
4. `documentacion/DEBUG_FLUJO_ACTIVACION_COMPLETO.md` (nuevo)
5. `documentacion/RESUMEN_SOLUCION_REDIRECT.md` (nuevo)

### Referencias

- **Informe del Error:** `documentacion/INFORME_ERROR_REDIRECT_TENANT.md`
- **Solución Detallada:** `documentacion/SOLUCION_REDIRECT_TENANT.md`
- **Debug Flujo Completo:** `documentacion/DEBUG_FLUJO_ACTIVACION_COMPLETO.md`

---

## 🔧 v2.28 - Solución Error 404 en `/activate/` para Tenants Privados

### Problema Identificado

Al acceder a `http://home.sintel.com/activate?token=...`, el sistema mostraba:

```
Page not found (404)
Using the URLconf defined in config.urls_public, Django tried these URL patterns...
```

**Causa Raíz:** `TenantMainMiddleware` resolvía el tenant correctamente pero **NO establecía `request.urlconf`**, causando que Django usara `ROOT_URLCONF` por defecto.

### Solución Implementada

**Nuevo Middleware:** `TenantURLConfMiddleware`

**Archivo:** `apps/public/tenants/middleware_urlconf.py`

```python
class TenantURLConfMiddleware:
    """
    Middleware que garantiza que request.urlconf se establezca correctamente
    para tenants privados.
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

### Archivos Creados/Modificados

1. `apps/public/tenants/middleware_urlconf.py` (nuevo)
2. `config/settings.py` (modificado - middleware agregado)
3. `scripts/auditoria_completa_routing.py` (actualizado - incluye verificación del nuevo middleware)
4. `documentacion/INFORME_AUDITORIA_404_ACTIVATE.md` (nuevo)
5. `documentacion/RESUMEN_SOLUCION_404_ACTIVATE.md` (nuevo)
6. `documentacion/arquitectura_general.md` (actualizado - v2.28)

### Verificación

La auditoría completa muestra:
```
✅ Tenant resuelto: home (schema: home)
✅ Tenant privado resuelto correctamente
✅ URLConf correcto: TENANT_URLCONF
✅ No se encontraron errores críticos
```

### Referencias

- **Informe Completo:** `documentacion/INFORME_AUDITORIA_404_ACTIVATE.md`
- **Resumen:** `documentacion/RESUMEN_SOLUCION_404_ACTIVATE.md`
- **Enrutamiento Hostname:** `documentacion/ENRUTAMIENTO_HOSTNAME_ESTABLE.md`

---

## 📊 Resumen de Cambios

### Problemas Resueltos

1. ✅ **v2.27**: Error de redirect después de activación - Solucionado usando URL absoluta
2. ✅ **v2.28**: Error 404 en `/activate/` - Solucionado con `TenantURLConfMiddleware`

### Mejoras Implementadas

1. ✅ **v2.27**: Redirect después de activación usa URL absoluta para garantizar resolución correcta del tenant
2. ✅ **v2.28**: Middleware `TenantURLConfMiddleware` garantiza que `request.urlconf` se establezca correctamente
3. ✅ **v2.28**: Script de auditoría completa actualizado para verificar el nuevo middleware
4. ✅ **v2.28**: Documentación completa actualizada en `arquitectura_general.md`

### Archivos de Documentación Creados

1. `documentacion/SOLUCION_REDIRECT_TENANT.md`
2. `documentacion/INFORME_ERROR_REDIRECT_TENANT.md`
3. `documentacion/DEBUG_FLUJO_ACTIVACION_COMPLETO.md`
4. `documentacion/RESUMEN_SOLUCION_REDIRECT.md`
5. `documentacion/INFORME_AUDITORIA_404_ACTIVATE.md`
6. `documentacion/RESUMEN_SOLUCION_404_ACTIVATE.md`
7. `documentacion/CHANGELOG_v2.27_v2.28.md` (este archivo)

---

## ✅ Estado Final

- ✅ **v2.27**: Problema de redirect solucionado
- ✅ **v2.28**: Problema de 404 solucionado
- ✅ **v2.28**: Middleware implementado y verificado
- ✅ **v2.28**: Documentación completa actualizada
- ✅ **v2.28**: Auditoría completa pasada sin errores

---

**Fecha:** 2026-01-30  
**Versión:** v2.28  
**Estado:** ✅ **COMPLETADO Y VERIFICADO**
